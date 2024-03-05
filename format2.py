# The format-2 has been completed
from flask import Flask, request, jsonify
import re

app = Flask(__name__)


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

    return companies


@app.route('/format-2', methods=['POST'])
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
    parsed_data = format2(npx_data)

    return jsonify(parsed_data)


if __name__ == '__main__':
    app.run(debug=True)
