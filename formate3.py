from flask import Flask, request, jsonify
import re

app = Flask(__name__)


def parse_npx_data(npx_data):
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

# Define a route for receiving the N-PX data


@app.route('/format-3', methods=['POST'])
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
    parsed_data = parse_npx_data(npx_data)

    return jsonify(parsed_data)


if __name__ == '__main__':
    app.run(debug=True)
