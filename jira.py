import sys
import json
import argparse
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urljoin


class JiraError(Exception):
    def __init__(self, code=None, message='', cause=None):
        super(JiraError, self).__init__(code, message, cause)

    def __repr__(self):
        return ("JiraError(code={code!r}, message={message!r}, cause={cause!r}"
                .format(code=self.code,
                        message=self.message,
                        cause=self.cause))


class Jira(object):
    REST_ENDPOINT_PREFIX = "rest/api/2/"

    def __init__(self, server, user, password):
        self.user = user
        self.pwd = password
        self.headers = {'Accept': 'application/json'}
        self.auth = HTTPBasicAuth(self.user, self.pwd)
        self.server = server

    def createOneIssue(self, fieldArgs=None, updateArgs=None):
        data = self.processUpdateFields(fieldArgs=fieldArgs, updateArgs=updateArgs)
        res = self.doJiraRequest('POST', 'issue', data=data)
        return res

    def doJiraRequest(self, method, endpoint, data=None):
        if not endpoint.startswith(self.REST_ENDPOINT_PREFIX):
            endpoint = urljoin(self.REST_ENDPOINT_PREFIX, endpoint)
        uri = urljoin(self.server, endpoint)

        body = {}
        status = ''
        try:
            response = requests.request(method, uri, json=data, headers=self.headers, auth=self.auth, verify=False)

            if response.status_code in [200, 201]:
                body = json.loads(response.content)
                status = 'success'
            else:
                try:
                    body = json.loads(response.content)
                except ValueError:
                    pass
                print('Failed to request jira {}, status code is :{}'.format(uri, response.status_code))
        except Exception as e:
            print('Exception {} happens when request jira {}'.format(e, uri))
        return status, body

    def processUpdateFields(self, fieldArgs=None, updateArgs=None):
        # checking that there is no field in both fieldArgs and updateArgs
        if fieldArgs is not None and updateArgs is not None:
            duplicate_fields = set(fieldArgs) & set(updateArgs)
            if duplicate_fields:
                raise JiraError(message=("Following fields are present in both fieldArgs "
                                         "and updateArgs: {}".format(list(duplicate_fields))))

        data = {}
        if fieldArgs is not None:
            fields_dict = {}
            for field in fieldArgs:
                fields_dict[field] = fieldArgs[field]
            data['fields'] = fields_dict

        if updateArgs is not None:
            update_dict = {}
            for field, actions in updateArgs.items():
                # Checking if the verbs listed in actions list are supported
                verbs = set.union(set(), *(action.keys() for action in actions))
                if verbs - set(self.UPDATE_VERBS):
                    raise JiraError(message=(
                        "Unsupported verbs in update query: {}\n"
                        "Expecting one of {}".format(list(verbs - set(self.UPDATE_VERBS)),
                                                     self.UPDATE_VERBS)))
                update_dict[field] = actions
            data['update'] = update_dict
        return data


def main():
    parser = argparse.ArgumentParser(
        prog='jira.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='',
        epilog='')
    parser.add_argument('--server', required=True)
    parser.add_argument('--user', required=True)
    parser.add_argument('--password', required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--issuetype', required=True)
    parser.add_argument('--summary', required=True)
    parser.add_argument('--description', required=True)
    parser.add_argument('--priority', required=True)
    parser.add_argument('--components',  nargs='+')
    parser.add_argument('--versions', nargs='+')
    parser.add_argument('--labels', nargs='+')
    args = parser.parse_args()
    field_args = {}
    field_args.setdefault('project', {})["key"] = args.project
    field_args.setdefault('issuetype', {})["name"] = args.issuetype
    field_args.setdefault('summary', args.summary)
    field_args.setdefault('description', args.description)

    if args.project == "OAM":
        field_args.setdefault('components', []).extend([{'name': c} for c in args.components or []])
        field_args.setdefault('versions', []).extend([{'name': c} for c in args.versions or []])
        field_args.setdefault('priority', {})["name"] = args.priority
        field_args.setdefault('customfield_15101', {})["value"] = "Free Testing"
        field_args.setdefault('customfield_14617', 'Integration Tests')
        field_args.setdefault('customfield_18202', []).append({"value": "BXT-RVP"})
        field_args.setdefault('customfield_14623', {})["value"] = "Development"

    if args.project == "CRJ":
        field_args.setdefault('priority', {})["name"] = args.priority
        field_args.setdefault('components', []).extend([{'name': c} for c in args.components or []])
        field_args.setdefault('labels', []).extend(args.labels or [])

    print(field_args)
    jira = Jira(args.server, args.user, args.password)
    status, body = jira.createOneIssue(fieldArgs=field_args, updateArgs={})
    if status == 'success':
        print('successfully created jira')
        print(body)
        sys.exit(0)
    else:
        sys.exit(body)


if __name__ == "__main__":
    main()
