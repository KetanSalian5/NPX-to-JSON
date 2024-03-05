from flask import Flask, request, jsonify
import re
app = Flask(__name__)


def format1(npx_data):
    funds = []
    companies = []
    current_fund = None
    current_company = None
    fund_details_match = None
    current_proposal = None

    lines = npx_data.split('\n')
    for index, line in enumerate(lines):
        # Check for fund name starting and ending with '=========='
        fund_match = re.match(r'^=+\s*([^=]+)\s*=+$', line,flags=re.IGNORECASE)
        if fund_match:
            if current_fund:
                # Check for the specific sentence before appending the current_fund
                if "There is no proxy voting activity for the fund" in current_fund["fund_text"]:
                    # Continue processing only if the sentence is present
                    funds.append(current_fund)
                current_fund = None  # Reset current_fund
            current_fund = {
                "fund_name": fund_match.group(1).strip(),
                "fund_text": ""
            }
        elif current_fund:
            # If line is not empty and does not end with '---------------------', append to fund_text
            if line.strip() != "" and not line.strip().endswith('---------------------'):
                current_fund["fund_text"] += " " + line.strip()

    # Append the last fund if present
    if current_fund:
        # Check if the fund text has more than 6 lines and sentences are within the character limit
        fund_text_lines = current_fund["fund_text"].strip().split('\n')
        if len(fund_text_lines) <= 6:
            current_fund["fund_text"] = ""
        else:
            # Filter out sentences longer than 115 characters
            filtered_fund_text = [sentence for sentence in fund_text_lines if len(sentence) <= 115]
            current_fund["fund_text"] = "\n".join(filtered_fund_text)
        # Check for the specific sentence before appending the current_fund
        if "There is no proxy voting activity for the fund" in current_fund["fund_text"]:
            # Continue processing only if the sentence is present
            funds.append(current_fund)

    lines = npx_data.split('\n')
    for index, line in enumerate(lines):
        # Skip lines containing only equal signs or lines starting and ending with equal signs
        if re.match(r'^[=]+$', line) or re.match(r'^[=]+\s*$', line):
            continue

        # Skip lines containing only dashes
        if re.match(r'^[-]+$', line):
            continue

        # Skip lines containing the specified phrase
        if "========== END NPX REPORT" in line:
            break

        # Check for fund name
        fund_match = re.match(r'^[=]+\s*([^=]+)\s*[=]+$', line, flags=re.IGNORECASE)
        #fund_match = re.match(r'^=======================\s+([^=]+)\s+=======================\s*$', line)
        if fund_match:
            fund_details_match = {"fund": fund_match.group(1).strip()}
            continue
        
        # Check for company details
        ticker_match = re.match(r'^Ticker:\s+([0-9A-Za-z.]*+)\s+Security ID:\s+([A-Z0-9]+[A-Za-z0-9]*)$', line)

        # print(company_match)
        if ticker_match:
            if current_company:
                # End of the previous company's details
                current_company = None
                # companies.append(current_company) 
            current_company = {
                "fund_details": fund_details_match,
                "company_name": lines[index-2],
                "ticker": ticker_match.group(1).strip(),
                "security_id": ticker_match.group(2).strip(),
                "meeting_date": "",
                "meeting_type": "",
                "record_date": "",
                "proposals": []
            }
            companies.append(current_company)
        elif current_company:
            # Check for company details
            # ticker_match = re.match(r'^Ticker:\s+([0-9A-Za-z.]*+)\s+Security ID:\s+([A-Z0-9]+[A-Za-z0-9]*)$', line)
            meeting_date_match = re.match(r'^Meeting Date:\s+([A-Z0-9\s,]+)\s+Meeting Type:\s+([A-Za-z/\s]+)$', line)
            record_date_match = re.match(r'^Record Date:\s+([A-Z0-9\s,]+)$', line)

            # if ticker_match:
                # current_company["ticker"] = ticker_match.group(1).strip()
                # current_company["security_id"] = ticker_match.group(2).strip()
            if meeting_date_match:
                current_company["meeting_date"] = meeting_date_match.group(1).strip()
                current_company["meeting_type"] = meeting_date_match.group(2).strip()
            elif record_date_match:
                current_company["record_date"] = record_date_match.group(1).strip()
            else:
                # Check for proposals
                proposal_match = re.match(r'^\s*([0-9A-Za-z.]+[a-zA-Z0-9]*\d*(?:\d+)?)\s+([^\n]+?)\s+(For|Against|None|One Year|Did Not Vote)\s+(.+)\s+(Management|Shareholder)$', line)

                if proposal_match:
                    current_proposal = {
                        "ballot_id": proposal_match.group(1).strip(),
                        "proposal": proposal_match.group(2).strip(),
                        "management_vote": proposal_match.group(3).strip(),
                        "vote_cast": proposal_match.group(4).strip(),
                        "sponsor": proposal_match.group(5).strip()if proposal_match.group(5) else None
                    }
                    current_company["proposals"].append(current_proposal)
                #elif current_proposal and "management_vote" in current_proposal and current_proposal["management_vote"] == "Against":
                    # Reset current_proposal for multiline proposals with management_vote "Against"
                    #current_proposal = None
                    #continue
                elif current_proposal:
                    # Append to the description for multiline proposals, excluding lines with only "=" or only dashes
                    splittedLine = line.split('      ')
                    if not re.match(r'^\s*#', line) and not re.match(r'^[-]+$', line) and len(splittedLine) >= 2 and splittedLine[0] == "":
                        current_proposal["proposal"] += " " + line.strip()

    
    if current_company:
        # companies.append(current_company)
        current_company = None
        
    return funds, companies

# Define a route for receiving the N-PX data
@app.route('/format-1', methods=['POST'])
def parse_npx():
    if 'npx' in request.files:
        # Handle form-data
        npx_file = request.files['npx']
        npx_data = npx_file.read().decode('utf-8')
    elif 'npx' in request.json:
        # Handle JSON
        npx_data = request.json['npx']
    else:
        return jsonify({"error": "No data provided"}), 400

    # Parse N-PX data
    parsed_data = format1(npx_data)

    return jsonify(parsed_data)

if __name__ == '__main__':
    app.run(debug=True)
