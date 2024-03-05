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
# ... (format-1 logic)

def format2(npx_data):
    companies = []
    current_company = None
    current_proposal = None
    lines = npx_data.split('\n')

    for line in lines:
        if not line.strip():
            continue
        if "* Management position unknown" in line:
            break
        # Extracting relevant information using regular expressions
        company_match = re.match(
            r'^\s*([A-Z0-9\s,.\'-]+)\s+Agenda Number:\s*(\d+)?\s*$', line)
        security_match = ""
        meeting_type_match = ""
        ticker_match = ""
        meeting_date_match = ""
        isin_match = re.search(r"ISIN:\s+([^\n]+)", line)

        if re.search(r'Security:', line) and re.search(r'Meeting Type:', line):
            pattern_match = re.split(r'\s{2,}', line)
            security_meeting_type = list(filter(None, pattern_match))

            security_match = security_meeting_type[1]
            meeting_type_match = security_meeting_type[3]

        if re.search(r'Ticker:', line) and re.search(r'Meeting Date:', line):
            pattern_match = re.split(r'\s{2,}', line)
            ticker_meeting_date = list(filter(None, pattern_match))

            ticker_match = ticker_meeting_date[1]
            meeting_date_match = ticker_meeting_date[3]

        if company_match:
            if current_company:
                companies.append(current_company)

            current_company = {
                "company_name": company_match.group(1).strip(),
                "agenda_number": company_match.group(2).strip() if company_match.group(2) else "",
                "securityId": "",
                "ticker": "",
                "ISIN": "",
                "meetingType": "",
                "meetingDate": "",
                "proposals": []
            }

        elif security_match and meeting_type_match:
            current_company["securityId"] = security_match
            current_company["meetingType"] = meeting_type_match

        elif ticker_match and meeting_date_match:
            current_company["ticker"] = ticker_match
            current_company["meetingDate"] = meeting_date_match

        elif isin_match:
            current_company["ISIN"] = isin_match.group(1).strip()

        elif current_company and line.strip() != "Prop.# Proposal Proposal Vote For/Against Management":
            proposal_direcor_match = re.match(
                r'^\s*(\S+)\s+(DIRECTOR)\s*$', line, re.IGNORECASE)

            proposal_director_names_match = re.match(
                r'^\s{2,}(Prop.#+)?([^\n]+?)\s+(Mgmt|Shr|Non-Voting)\s+(Withheld|For|Against|1 Year|Abstain)\s+(.+)$', line, re.IGNORECASE)

            proposal_match = re.match(
                r'^\s*([0-9A-Z.]+[a-zA-Z]*)\s+([^\n]+?)\s+(Mgmt|Shr|Non-Voting)\s+(Withheld|For|Against|1 Year|Abstain)\s+(.+)$', line, re.IGNORECASE)

            cmmt_proposal_match = re.match(
                r'^\s*(CMMT\s+)?(.*?)\s+(Non-Voting)$', line, re.IGNORECASE)

            if proposal_direcor_match:
                current_proposal = {
                    "ballot_id": proposal_direcor_match.group(1).strip(),
                    "is_director": proposal_direcor_match.group(2).strip(),
                    "proposals": "",
                    "proposals_type": "",
                    "proposal_Vote": "",
                    "sponsor": "",
                }
            elif proposal_director_names_match and not (re.match(r'^\s*Prop.#+ ', line)):
                current_proposal.update({
                    "proposals": current_proposal.get("proposals", "") + " " + proposal_director_names_match.group(2).strip(),
                    "proposals_type": proposal_director_names_match.group(3).strip(),
                    "proposal_Vote": proposal_director_names_match.group(4).strip() if proposal_director_names_match.group(4) is not None else "",
                    "sponsor": proposal_director_names_match.group(5).strip() if proposal_director_names_match.group(5) is not None else "",
                })
                current_company["proposals"].append(current_proposal)
            elif proposal_match:
                current_proposal = {
                    "ballot_id": proposal_match.group(1).strip(),
                    "proposals": proposal_match.group(2).strip(),
                    "proposals_type": proposal_match.group(3).strip(),
                    "proposal_Vote": proposal_match.group(4).strip() if proposal_match.group(4) is not None else "",
                    "sponsor": proposal_match.group(5).strip() if proposal_match.group(5) is not None else "",
                }
                current_company["proposals"].append(current_proposal)
            elif cmmt_proposal_match:
                current_proposal = {
                    "ballot_id": cmmt_proposal_match.group(1).strip() if cmmt_proposal_match.group(1) is not None else "",
                    "proposals": cmmt_proposal_match.group(2).strip(),
                    "proposals_type": cmmt_proposal_match.group(3).strip(),
                    "proposal_Vote": "",
                    "sponsor": "",
                }
                current_company["proposals"].append(current_proposal)
            elif current_proposal:
                # Append to the description for multiline proposals
                if not (re.match(r'^\s*Prop.#+ ', line)
                        or re.match(r'^\s*Type\s+Management\s*$', line)
                        or re.match(r'^[-]+$', line)
                        or re.match(r'^\s*(The fund held no voting securities during the reporting period and did not vote any securities or have\s*|any securities that were subject to a vote during the reporting period\.\s*)$', line)):
                    current_proposal["proposals"] += " " + line.strip()

    if current_company:
        companies.append(current_company)

    return companies   # ... (format-2 logic)
   
def format3(npx_data):
    companies = []
    current_company = None
    current_proposal = None
    no_company = {
        "fund_name": "",
        "fund_details": "",
    }

    lines = npx_data.split('\n')
    fund_name = ''

    for line in lines:
        # Skip lines containing only underscores
        if re.match(r'^[-]+$', line):
            continue

        if (re.match(r'.*Fund$', line)):
            fund_name = line.strip()
            no_company = {
                "fund_name": fund_name,
                "fund_details": "",
            }
            continue

        if (re.match(r'^\s*(The fund held no voting securities during the reporting period and did not vote any securities or have\s*|any securities that were subject to a vote during the reporting period\.\s*)$', line)):
            no_company["fund_details"] += line.strip()

            if (re.match(r'^\s*any securities that were subject to a vote during the reporting period\.\s*$', line)):
                companies.append(no_company)
                continue
         # Skip lines containing the specified phrase
        if "* Management position unknown" in line:
            break

        # Check for company name and agenda number
        company_agenda_match = re.match(
            r'^\s*([A-Z0-9\s,.\'-]+)\s+Agenda Number:\s*(\d+)?\s*$', line)
        if company_agenda_match:
            if current_company:
                companies.append(current_company)
            current_company = {
                "fund_name": fund_name,
                "company_name": company_agenda_match.group(1).strip(),
                "agenda_number": company_agenda_match.group(2).strip() if company_agenda_match.group(2) else "",
                "proposals": []
            }
        elif current_company:
            # Check for company details
            details_match = re.match(
                r'^\s*(Security|Meeting Type|Meeting Date|Ticker|ISIN):\s*(.+)?$', line)

            if details_match:
                current_details_key = details_match.group(1).strip()
                try:
                    current_details_value = details_match.group(2).strip()
                except AttributeError:
                    current_details_value = ""
                current_company = {**current_company, **
                                   {"_".join(current_details_key.lower().split()): current_details_value}}

                # Append to the value for multiline details
            else:
                # Check for proposals # i use re.IGNORECASE for ignore case-insensitive
                proposal_direcor_match = re.match(
                    r'^\s*(\S+)\s+(DIRECTOR)\s*$', line, re.IGNORECASE)

                proposal_director_names_match = re.match(
                    r'^\s{2,}()([^\n]+?)\s+(Mgmt|Shr|Non-Voting)\s+(Withheld|For|Against|1 Year|Abstain)\s+(.+)$', line, re.IGNORECASE)

                proposal_match = re.match(
                    r'^\s*([0-9A-Z.]+[a-zA-Z]*)\s+([^\n]+?)\s+(Mgmt|Shr|Non-Voting)\s+(Withheld|For|Against|1 Year|Abstain)\s+(.+)$', line, re.IGNORECASE)

                cmmt_proposal_match = re.match(
                    r'^\s*(CMMT\s+)?(.*?)\s+(Non-Voting)$', line, re.IGNORECASE)

                if proposal_direcor_match:
                    current_proposal = {
                        "ballet_id": proposal_direcor_match.group(1).strip(),
                        "is_director": proposal_direcor_match.group(2).strip(),
                        "proposals": "",
                        "proposals_type": "",
                        "proposal_Vote": "",
                        "sponsor": "",
                    }
                elif proposal_director_names_match and not (re.match(r'^\s*Prop.#+ ', line)):
                    current_proposal = {
                        **current_proposal,
                        "proposals": current_proposal["is_director"]+": "+proposal_director_names_match.group(2).strip(),
                        "proposals_type": proposal_director_names_match.group(3).strip(),
                        "proposal_Vote": proposal_director_names_match.group(4).strip() if proposal_director_names_match.group(4) is not None else "",
                        "sponsor": proposal_director_names_match.group(5).strip() if proposal_director_names_match.group(5) is not None else "",
                    }
                    current_company["proposals"].append(current_proposal)
                    continue
                elif proposal_match:
                    current_proposal = {
                        "ballet_id": proposal_match.group(1).strip(),
                        "proposals": proposal_match.group(2).strip(),
                        "proposals_type": proposal_match.group(3).strip(),
                        "proposal_Vote": proposal_match.group(4).strip() if proposal_match.group(4) is not None else "",
                        "sponsor": proposal_match.group(5).strip() if proposal_match.group(5) is not None else "",
                    }
                    current_company["proposals"].append(current_proposal)
                elif cmmt_proposal_match:
                    current_proposal = {
                        "ballet_id": cmmt_proposal_match.group(1).strip() if cmmt_proposal_match.group(1) is not None else "",
                        "proposals": cmmt_proposal_match.group(2).strip(),
                        "proposals_type": cmmt_proposal_match.group(3).strip(),
                        "proposal_Vote": "",
                        "sponsor": "",
                    }
                    current_company["proposals"].append(current_proposal)
                elif current_proposal:
                    # Append to the description for multiline proposals
                    if not (re.match(r'^\s*Prop.#+ ', line)
                            or re.match(r'^\s*Type\s+Management\s*$', line)
                            or re.match(r'^[-]+$', line)
                            or re.match(r'^\s*(The fund held no voting securities during the reporting period and did not vote any securities or have\s*|any securities that were subject to a vote during the reporting period\.\s*)$', line)):
                        current_proposal["proposals"] += " " + line.strip()
    if current_company:
        companies.append(current_company)

    return companies
    # ... (format-3 logic)

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

    return result    # ... (format-4 logic)


@app.route('/format-1', methods=['POST'])
def parse_format_1():
    if 'npx' in request.files:
        npx_file = request.files['npx']
        npx_data = npx_file.read().decode('utf-8')
    elif 'npx' in request.json:
        npx_data = request.json['npx']
    else:
        return jsonify({"error": "No data provided"}), 400

    parsed_data = format1(npx_data)
    return jsonify(parsed_data)

@app.route('/format-2', methods=['POST'])
def parse_format_2():
    if 'npx' in request.files:
        npx_file = request.files['npx']
        npx_data = npx_file.read().decode('utf-8')
    elif 'npx' in request.json:
        npx_data = request.json['npx']
    else:
        return jsonify({"error": "No data provided"}), 400

    parsed_data = format2(npx_data)
    return jsonify(parsed_data)

@app.route('/format-3', methods=['POST'])
def parse_format_3():
    if 'npx' in request.files:
        npx_file = request.files['npx']
        npx_data = npx_file.read().decode('utf-8')
    elif 'npx' in request.json:
        npx_data = request.json['npx']
    else:
        return jsonify({"error": "No data provided"}), 400

    parsed_data = format3(npx_data)
    return jsonify(parsed_data)

@app.route('/format-4', methods=['POST'])
def parse_format_4():
    if 'npx' in request.files:
        npx_file = request.files['npx']
        npx_data = npx_file.read().decode('utf-8',errors='ignore')
    elif 'npx' in request.json:
        npx_data = request.json['npx']
    else:
        return jsonify({"error": "No data provided"}), 400

    parsed_data = format4(npx_data)
    return jsonify(parsed_data)


if __name__ == '__main__':
    app.run(debug=True)
