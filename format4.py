from flask import Flask, request, jsonify
import re

app = Flask(__name__)


def format4(txt_content):
    companies = re.split(r'_{20,}', txt_content)

    result = []
    fund_name = ""

    if companies[0]:
        lines = companies[0].split('\n')
        lines = [line.strip()
                 for line in lines if line.strip()]

        for no_fund_line in lines:
            if re.match(r'^Fund Name : .+$', no_fund_line):
                fundName = no_fund_line.split(":")
                fund_name = fundName[1].strip() if fundName[1] else ''
                continue

            if re.search(r'The fund did not vote proxies relating to portfolio', no_fund_line):
                fund_text = "The fund did not vote proxies relating to portfolio securities during the period covered by this report."
                fund_details = {
                    "fund_name": fund_name,
                    "fund_text": fund_text.strip()
                }
                result.append(fund_details)
                continue

    for company in companies[1:]:
        lines = company.split('\n')
        lines = [line.strip()
                 for line in lines if line.strip()]

        if lines:
            company_data = {
                "company_name": lines[0].strip(),
                "fund_name": fund_name.strip(),
                "ticker": "",
                "security_id": "",
                "meeting_date": "",
                "meeting_status": "",
                "meeting_type": "",
                "country": "",
                "proposals": []
            }

            proposals = []
            columnHeaders = []

            def array_contains_values(arr, values):
                return all(value in arr for value in values)

            for company_line in lines[1:]:
                stripped_line = company_line.strip()
                
                if (re.search(r'Item1 Proxy Voting Record', stripped_line) or re.search(r'Registrant :', stripped_line) or re.search(r'Date of fiscal year', stripped_line) or re.search(r'In all markets', stripped_line) or re.search(r'Key-', stripped_line)):
                    continue
                if re.search(r'----', stripped_line) and len(stripped_line) > 10:
                    
                    continue

                if re.match(r'^Fund Name : .+$', stripped_line):
                    fundName = stripped_line.split(":")
                    fund_name = fundName[1].strip() if fundName[1] else ''
                    continue

                if re.search(r'The fund did not vote proxies relating to portfolio', stripped_line):
                    fund_text = "The fund did not vote proxies relating to portfolio securities during the period covered by this report."
                    fund_details = {
                        "fund_name": fund_name,
                        "fund_text": fund_text.strip()
                    }
                    result.append(fund_details)
                    continue

                if re.match(r'^\s*Ticker\s+Security ID:\s+Meeting Date\s+Meeting Status\s*$', stripped_line):
                    columnHeaders = re.split(r'\s{2,}', stripped_line.strip())
                    continue

                if array_contains_values(columnHeaders, ["Ticker", "Security ID:", "Meeting Date", "Meeting Status"]):
                    columnValues = re.split(r'\s+', stripped_line.strip())

                    company_data['ticker'] = columnValues[0]
                    company_data['security_id'] = (columnValues[1] if columnValues[1] else "") + " " +\
                        (columnValues[2] if columnValues[2] else "")
                    company_data['meeting_date'] = (
                        columnValues[3] if columnValues[3] else "")
                    company_data['meeting_status'] = (
                        columnValues[4] if columnValues[4] else "")

                    if len(columnValues) > 5:
                        company_data['meeting_status'] += " " + \
                            (columnValues[5] if columnValues[5] else "") + " "
                    if len(columnValues) > 6:
                        company_data['meeting_status'] += columnValues[6] if columnValues[6] else ""
                    columnHeaders = []
                    continue

                if re.match(r'^\s*Meeting Type\s+Country of Trade\s*$', stripped_line):
                    columnHeaders = re.split(r'\s{2,}', stripped_line.strip())
                    continue

                if array_contains_values(columnHeaders, ["Meeting Type", "Country of Trade"]):
                    columnValues = re.split(r'\s{2,}', stripped_line.strip())
                    company_data["meeting_type"] = columnValues[0] if columnValues[0] else ""
                    company_data["country"] = columnValues[1] if columnValues[1] else ""

                    columnHeaders = []
                    continue

                if stripped_line.startswith("Issue No."):
                    current_proposal = None
                    continue
                else:
                    pattern = re.match(
                        r'^\s*([0-9A-Z.]+[a-zA-Z]*)\s+([^\n]+?)\s+(Mgmt|ShrHoldr|Non-Voting|N/A)\s+(Withhold|For|Against|1 Year|N/A|Abstain|TNA)\s+(.+)\s+(.+?)(?:\s+(.+))?$', stripped_line, re.IGNORECASE)

                    if pattern:
                        current_proposal = {
                            "ballot_id": pattern.group(1).strip(),
                            "proposal": pattern.group(2).strip(),
                            "proposal_ype": pattern.group(3).strip(),
                            "management_vote": pattern.group(4).strip(),
                            "vote_cast": pattern.group(5).strip(),
                            "for_against_mgmt": pattern.group(6).strip() if pattern.group(6) else ""
                        }
                        proposals.append(current_proposal)
                    elif current_proposal:
                        if not re.match(r'^\s*#', stripped_line) and "<PAGE>" not in stripped_line and "22</pre>" not in stripped_line  and "</pre>" not in stripped_line:
                            current_proposal["proposal"] += " " + \
                                stripped_line
                        elif "<PAGE>" in stripped_line or "22</pre>" in stripped_line or "</pre>" in stripped_line:
                                break

                    company_data['proposals'] = proposals

            result.append(company_data)

    return result
# Define a route for receiving the N-PX data


@app.route('/format-4', methods=['POST'])
def parse_npx():
    if 'npx' in request.files:
        # Handle form-data
        npx_file = request.files['npx']
        npx_data = npx_file.read().decode('utf-8', errors='ignore')
    elif 'npx' in request.json:
        # Handle JSON
        npx_data = request.json['npx']
    else:
        return jsonify({"error": "No data provided"}), 400

    # Parse N-PX data
    parsed_data = format4(npx_data)

    return jsonify(parsed_data)


if __name__ == '__main__':
    app.run(debug=True)
