#!/usr/bin/python

import requests
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = '''
---
module: fosshost_aarch64_vm
short_description: Manage Fosshost aarch64 VMs
version_added: "0.0.1"
description:
    - "Manage VMs on the Fosshost aarch64 platform."

options:
    api_key:
        description:
            - Platform API key
        required: true
    id:
        description:
            - VM ID (Only used when state=absent to delete a VM)
        required: false

    project:
        description:
            - Project to add VM to (Only used when creating a VM)
        required: false

    hostname:
        description:
            - VM Hostname (Only used when creating a VM)
        required: false

    plan:
        description:
            - VM Plan (Only used when creating a VM)
        required: false

    os:
        description:
            - VM Operating System (Only used when creating a VM)
        required: false

    pop:
        description:
            - Point of Presence to provision VM in (Only used when creating a VM)
        required: false

author:
    - Nate Sales (@natesales)
'''

EXAMPLES = '''
# Create a new VM
- name: Create a VM
  aarch64_vm:
    api_key: "iK3K8oSb9jWw2L+ufESfGvzpnrp/0pOr2Rh9kc"
    hostname: "anton-k8s-ingress.piedpiper.com"
    project: "5nzn9b3JHeY56fz9UMaQ3brFLZahZw"
    plan: "v1.small"
    os: "debian"
    pop: "dfw"
  register: vm_create

# Delete the newly created VM
- name: Delete a VM
  aarch64_vm:
    api_key: "iK3K8oSb9jWw2L+ufESfGvzpnrp/0pOr2Rh9kc"
    id: "{{ vm_create.vm._id }}"
    state: "absent"
'''

RETURN = '''
message:
    description: Raw message from the API
    type: str
vm:
    description: New VM document (Only returned when creating a VM)
'''


class ApiException(Exception):
    """Exception returned by the API"""

    def __init__(self, message: str):
        self.message: str = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class Aarch64Client:
    """Client for the aarch64.com API"""
    api_key: str = ""
    server: str = "https://console.aarch64.com/api"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _req(self, method: str, endpoint, body: dict = None) -> requests.Response:
        resp = requests.request(method, self.server + endpoint, json=body, headers={"Authorization": self.api_key})
        if not resp.status_code == 200:
            raise ApiException(f"API returned HTTP {resp.status_code}")

        if not resp.json()["meta"]["success"]:
            raise ApiException(resp.json()["meta"]["message"])

        return resp

    def projects(self):
        """Get list of projects"""
        return self._req("GET", "/projects")

    def create_project(self, name: str):
        """Create a project"""
        return self._req("POST", "/project", {"name": name})

    def add_user(self, project_id: str, email: str):
        """Add a user to a project"""
        return self._req("POST", "/project/adduser", {"project": project_id, "email": email})

    def create_vm(self, hostname: str, pop: str, project_id: str, plan: str, os: str):
        """Create a new VM"""
        return self._req("POST", "/vms/create", {
            "hostname": hostname,
            "pop": pop,
            "project": project_id,
            "plan": plan,
            "os": os
        })

    def delete_vm(self, vm: str):
        """Delete a VM"""
        return self._req("DELETE", "/vms/delete", {"vm": vm})

    def get_system(self):
        """Get system information"""
        return self._req("GET", "/system")


def main():
    # Module arguments
    module = AnsibleModule(argument_spec=dict(
        api_key=dict(required=True, type="str"),
        id=dict(required=False, type="str"),
        hostname=dict(required=False, type="str"),
        project=dict(required=False, type="str"),
        plan=dict(required=False, type="str"),
        os=dict(required=False, type="str"),
        pop=dict(required=False, type="str"),
        state=dict(default="present", choices=["present", "absent"])
    ))

    # Result to return
    result = {"changed": False}

    client = Aarch64Client(module.params["api_key"])

    if module.params["state"] == "present":
        try:
            projects_request = client.projects()
        except ApiException as e:
            module.fail_json(msg=f"Unable to get projects: {e}")
        else:
            project = {}
            for _project in projects_request.json()["data"]:
                if _project["_id"] == module.params["project"]:
                    project = _project
            if project == {}:
                module.fail_json(msg=f"Unable to find project with id {module.params['project']}")

            try:
                create_request = client.create_vm(module.params.get("hostname"),
                                                  module.params.get("pop"),
                                                  module.params.get("project"),
                                                  module.params.get("plan"),
                                                  module.params.get("os"))
            except ApiException as e:
                module.fail_json(msg=f"Unable to create VM: {e}")
            else:
                result["vm"] = create_request.json()["data"]
                result["message"] = create_request.json()["meta"]["message"]
                result["changed"] = True
    elif module.params["state"] == "absent":
        try:
            delete_request = client.delete_vm(module.params.get("id"))
        except ApiException as e:
            module.fail_json(msg=f"Unable to delete VM: {e}")
        else:
            result["message"] = delete_request.json()["meta"]["message"]
            result["changed"] = True

    module.exit_json(**result)


if __name__ == "__main__":
    main()
