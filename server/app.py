# Copyright 2025 UBC Quantum Software and Algorithms Research Lab

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This is the main flask application that responds to user requests,
does most of the processing for debugging other than the main code
execution, and interacts with the database.
"""

from flask import Flask, request, jsonify, Response
import dill as pickle
import matplotlib
import json
from pymongo import MongoClient
import string
import random
import time
import requests
from server import helpers
import pennylane as qml

matplotlib.use("Agg")


EXEC_SERVER_URL = "http://localhost:5001"

NOAUTH = True


def create_app(test_config={}):
    """Main flask application function.

    Args:
        test_config: Configuration used by Pytest
            to disable untestable user authentication systems.

    Returns:
        flask application
    """
    db_client = MongoClient("localhost", 27017)
    db = db_client.circinspect
    db_sessions = db.sessions
    db_users = db.users
    db_bugs = db.bugs

    app = Flask(__name__, instance_relative_config=True)
    app.json.default = helpers.json_default

    def find_user_by_token(token):
        """Find the database entry for user with the token.

        Args:
            token: the token user received for authentication

        Returns:
            If auth is on:
             1. Returns user data that is associated with the token
                if the data is present in the database.
             2. If no user is associated with the token, "None" is returned.
            If auth is off, a default object is returned that will
            allow authentication on other functions to always pass.
        """
        if NOAUTH:
            return {"email_address": "NOAUTH"}
        if type(token) is not str:
            return None
        user = db_users.find_one({"token": token})
        if type(user) is not dict:
            return None
        if user.get("expires", 0) < time.time():
            return None
        return user

    @app.route("/visualizeCircuit", methods=["POST"])
    def visualize_on_exec_server():
        """Send the user code to the execution server after
        the restricted code checks pass.

        Returns:
            The response sent back by the execution server
            is returned to user as a response.
        """
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if body:
            if (find_user_by_token(body.get("token", None)) is None) and not test_config.get(
                "TESTMODE", False
            ):
                return Response(status=401)
            data = {
                "api_call": "/visualizeCircuit",
                "timestamp": body["timestamp"],
                "code": body["data"],
            }
            if body["policy_accepted"]:
                db_sessions.update_one(
                    {"session_id": body["session_id"]},  # filter
                    {"$push": {"actions": data}},  # update
                )

            code_received = body["data"]
            # initial check for malicious code
            restricted_code = helpers.check_for_restricted_code(code_received)
            if restricted_code != "":
                return jsonify({"error": restricted_code})

            # send code to exec server to get the trace
            res = requests.post(EXEC_SERVER_URL, json={"data": code_received})
            if res.status_code == 418:
                return jsonify({"error": ["Time limit exceeded", "line unknown"]})

            if res.status_code == 400:
                return jsonify({"error": ["Please run a quantum circuit", "line unknown"]})
            return res.json()

    @app.route("/expandMethod", methods=["POST"])
    def expand_method():
        """Compute the next level of the subroutine expansion tree
        including the visualizations for the level.

        Returns:
            JSON used by the frontend to add the expansions to the GUI
        """
        body = json.loads(request.data.decode("utf-8"))
        if body:
            if (find_user_by_token(body.get("token", None)) is None) and not test_config.get(
                "TESTMODE", False
            ):
                return Response(status=401)
            (commands, annotated_queue) = pickle.loads(bytes.fromhex(body["commands"]))
            device_name = body["device_name"]
            identifier = body["id"]
            num_wires = body["num_wires"]
            num_shots = body["num_shots"]
            end_idx = body["end_idx"]
            if end_idx == "-1":
                if "real_time" in body:
                    output = helpers.expand_methods(
                        commands,
                        identifier,
                        device_name,
                        num_wires,
                        num_shots,
                        annotated_queue,
                        show_measurements=False,
                        all_commands=commands,
                    )
                else:
                    output = helpers.expand_methods(
                        commands,
                        identifier,
                        device_name,
                        num_wires,
                        num_shots,
                        annotated_queue,
                        show_measurements=True,
                        all_commands=commands,
                    )
            else:
                output = helpers.expand_methods(
                    commands[0 : int(end_idx)],
                    identifier,
                    device_name,
                    num_wires,
                    num_shots,
                    annotated_queue,
                    show_measurements=False,
                    all_commands=commands,
                )

            output_to_send = jsonify(output)

            for c in output["children"]:
                c.pop("image", None)

            data = {
                "api_call": "/expandMethod",
                "timestamp": body["timestamp"],
                "expanded_function": body["name"],
                "output": jsonify(output).json,
            }
            if body["policy_accepted"]:
                db_sessions.update_one(
                    {"session_id": body["session_id"]},  # filter
                    {"$push": {"actions": data}},  # update
                )

            return output_to_send

    @app.route("/debugNext", methods=["POST"])
    def debug_next():
        """Compute the next point where the debugger needs to stop,
            Redo the pennylane computations until the new stop point,
            Compute the results and visualizations until this point.

        Returns:
            JSON for frontend to render the GUI with new results.
        """
        process_start_time = time.time()
        exec_time_list = []
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if body:
            if (find_user_by_token(body.get("token", None)) is None) and not test_config.get(
                "TESTMODE", False
            ):
                return Response(status=401)
            data = {
                "api_call": "/debugNext",
                "timestamp": body["timestamp"],
                "breakpoints": body["data"],
                "debug_index": body["debug_index"],
            }
            if body["policy_accepted"]:
                db_sessions.update_one(
                    {"session_id": body["session_id"]},  # filter
                    {"$push": {"actions": data}},  # update
                )
            device_name = body["device_name"]
            debug_index = int(body["debug_index"])
            num_wires = int(body["num_wires"])
            num_shots = int(body["num_shots"])
            debug_action = body["debug_action"]
            (commands, _) = pickle.loads(bytes.fromhex(body["commands"]))
            found_new_debug_idx = False
            debug_lines = set()
            if len(body["data"]) != 0:
                for line in body["data"].split(" "):
                    debug_lines.add(line)

            # Data from user is set up, do debug operations
            # select next index to stop the circuit building and debug
            if debug_action == "next_breakpoint":
                for i in range(debug_index + 1, len(commands)):
                    if str(commands[i].line_number) in debug_lines:
                        debug_index = i
                        found_new_debug_idx = True
                        break
            elif debug_action == "prev_breakpoint":
                for i in range(debug_index - 1, 0, -1):
                    if str(commands[i].line_number) in debug_lines:
                        debug_index = i
                        found_new_debug_idx = True
                        break
            elif debug_action == "step_over":
                curr_function = commands[debug_index].function
                if commands[debug_index].identifier_its_called_from is None:
                    grandpa_id = None
                else:
                    p = commands[debug_index].identifier_its_called_from
                    grandpa_id = commands[p].identifier_its_called_from

                for i in range(debug_index + 1, len(commands)):
                    if (
                        commands[i].function == curr_function
                        or str(commands[i].line_number) in debug_lines
                        or (commands[i].identifier_its_called_from == grandpa_id)
                    ):
                        debug_index = i
                        found_new_debug_idx = True
                        break
            elif debug_action == "step_into":
                if debug_index + 1 < len(commands):
                    debug_index += 1
                    found_new_debug_idx = True
            elif debug_action == "step_out":
                if commands[debug_index].identifier_its_called_from is None:
                    grandpa_id = None
                else:
                    p = commands[debug_index].identifier_its_called_from
                    grandpa_id = commands[p].identifier_its_called_from

                for i in range(debug_index + 1, len(commands)):
                    if str(commands[i].line_number) in debug_lines or (
                        commands[i].identifier_its_called_from == grandpa_id
                    ):
                        debug_index = i
                        found_new_debug_idx = True
                        break
            elif debug_action == "restart":
                debug_index = 0
                found_new_debug_idx = True

            if not found_new_debug_idx:  # if no more breakpoints
                commands_to_execute_for_identifier = helpers.get_commands_to_execute_for_identifier(
                    commands, commands[0].identifier
                )
                circuit_img_base_64_byte_code = helpers.get_image_bs64_bytecode(
                    helpers.draw_circuit(
                        commands_to_execute_for_identifier,
                        device_name,
                        num_wires,
                        num_shots,
                        commands[-1].code_line,
                        commands,
                        real_time=False,
                    )
                )
                debug_index = -1
                line_number_to_highlight = -1
            else:  # if a valid breakpoint is present
                commands_to_execute_for_identifier = helpers.get_commands_to_execute_for_identifier(
                    commands[0:debug_index], commands[0].identifier
                )
                if (
                    len(commands_to_execute_for_identifier) > 0
                    and commands_to_execute_for_identifier[-1].line_type == "return"
                    and commands[-1].function == commands_to_execute_for_identifier[-1].function
                ):
                    commands_to_execute_for_identifier = commands_to_execute_for_identifier[0:-1]
                circuit_img_base_64_byte_code = helpers.get_image_bs64_bytecode(
                    helpers.draw_circuit(
                        commands_to_execute_for_identifier,
                        device_name,
                        num_wires,
                        num_shots,
                        commands[-1].code_line,
                        commands,
                        real_time=False,
                    )
                )
                line_number_to_highlight = str(commands[debug_index].line_number)
            if debug_index == -1:
                debug_index = len(commands)
            exec_time = time.time()
            circuit_output = helpers.run_pennylane_commands(
                commands[:-1],
                device_name,
                num_wires,
                num_shots,
                commands[-1].code_line,
                debug_index,
            )
            exec_time_list.append(time.time() - exec_time)

            has_children = False
            for c in commands_to_execute_for_identifier:
                if c.line_type == "call":
                    has_children = True
                    break

            process_end_time = time.time()
            # remove exec times from processing time
            processing_time = process_end_time - process_start_time
            for n in exec_time_list:
                processing_time -= n
            # Send data back to user
            return jsonify(
                {
                    "name": commands[0].function,
                    "id": commands[0].identifier,
                    "image": circuit_img_base_64_byte_code,
                    "line_number": commands[0].line_number,
                    "line_number_to_highlight": line_number_to_highlight,
                    "children": [],
                    "has_children": has_children,
                    "more_information": [],
                    "arguments": "",
                    "transform_details": "",
                    "end_idx": str(debug_index),
                    "circuit_output": repr(circuit_output).replace("\n", "").replace(" ", ""),
                    "debug_index": debug_index,
                    "processing_time_no_exec_times": processing_time,
                    "exec_times_list": exec_time_list,
                }
            )
        return jsonify({})

    @app.route("/auth/send", methods=["POST"])
    def send_login_user():
        """Send email to the user including the link for them to login
            to CircInspect after checking that the email is in the allowlist.
            The link includes a token generated by this function.
            Save the new user information and token to the database.

        Returns:
            REST Response with status code 204 if email is sent, 401 if error.
        """
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if body:
            email_address = body["email"]
            if "@" not in email_address:
                return Response(status=401)

            if not check_allowlist(email_address):
                return Response(status=401)

            # generate random token
            token = "".join(random.choices(string.ascii_letters + string.digits, k=9))

            # save token to database for use in verify_user()
            user = db_users.find_one({"email_address": email_address})
            if user is None:
                # first login
                db.users.insert_one(
                    {
                        "email_address": email_address,
                        "token": token,
                        "activated": int(time.time()),
                        "expires": int(time.time()) + 86400,  # 24h
                        "past_tokens": [],
                        "sessions": [],
                    }
                )
            else:
                activated = user.get("activated", None)
                if activated is not None:
                    if time.time() - activated < 5:
                        # user is spamming send button, do not generate token
                        return Response(status=204)
                    past_token = {
                        "token": user.get("token", ""),
                        "activated": user.get("activated", 0),
                        "expires": user.get("expires", 0),
                        "deactivated": min(user.get("expires", 0), int(time.time())),
                    }
                    db_users.update_one(
                        {"email_address": email_address},  # filter
                        {"$push": {"past_tokens": past_token}},  # update
                    )
                db_users.update_one(
                    {"email_address": email_address},
                    {
                        "$set": {
                            "token": token,
                            "activated": int(time.time()),
                            "expires": int(time.time()) + 86400,
                        }
                    },
                )

            # Because we do not use a mail client at the moment:
            print("Use link http://localhost:3000?" + token + " for " + email_address)
            return Response(status=204)

    def check_allowlist(email_address):
        """Check that the email address is allowed to login using allowlist

        Args:
            email_address (string): user's email address

        Returns:
            Boolean: True if email address is in the list or from a domain in
            the list, False otherwise.
        """

        allowEmail = False
        with open("allowlist.txt") as file:
            for line in file:
                if "@" in line:
                    if line.split("\n")[0] == email_address:
                        allowEmail = True
                        break
                else:
                    allow_domain = line.split("\n")[0].split(".")
                    email_domain = email_address.split("@")[1].split(".")
                    if len(email_domain) < len(allow_domain):
                        continue
                    correct = True
                    for i in range(len(allow_domain)):
                        if email_domain[-1 - i] != allow_domain[-1 - i]:
                            correct = False
                            break
                    if correct:
                        allowEmail = True
                        break
        return allowEmail

    @app.route("/auth/verify", methods=["POST"])
    def verify_user():
        """If auth is enabled, use the token sent by frontend
            to verify that the user has access to the application.

        Returns:
            JSON for frontend to use to render GUI.
        """
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if body:
            user = find_user_by_token(body.get("token", None))
            if user is None:
                return Response(status=401)
            return jsonify({"email": user["email_address"], "pennylane": qml.__version__})

    @app.route("/dc/sessionEnter", methods=["POST"])
    def collect_session_enter():
        """Handle data collection request that is sent when the user
            enters application or accepts data collection policy.
            If a sesion entry is not recorded, no data will be recorded
            from that session. This request does not affect user's
            interaction with the app.

        Returns:
            Empty REST response with appropriate status code.
        """
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if body:
            user = find_user_by_token(body.get("token", None))
            if user is None:
                return Response(status=401)
            data = {
                "session_id": body["session_id"],
                "session_start_timestamp": body["timestamp"],
                "user_ip": request.remote_addr,
                "user_token": body["token"],
                "user_email": user["email_address"],
                "actions": [{"api_call": "/dc/sessionEnter", "timestamp": body["timestamp"]}],
            }
            if body["policy_accepted"]:
                db_sessions.insert_one(data)
                db_users.update_one(
                    {"token": body["token"]}, {"$push": {"sessions": body["session_id"]}}
                )
            return Response(status=204)

    @app.route("/dc/sessionExit", methods=["POST"])
    def collectSessionExit():
        """Handle data collection request that is sent when the user exits.
            This request does not affect user's interaction with the app.
            Data is recorded only if user accepted the data collection policy.

        Returns:
            Empty REST response with appropriate status code.
        """
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if body:
            if find_user_by_token(body.get("token", None)) is None:
                return Response(status=401)
            data = {"api_call": "/dc/sessionExit", "timestamp": body["timestamp"]}
            if body["policy_accepted"]:
                db_sessions.update_one(
                    {"session_id": body["session_id"]},  # filter
                    {"$push": {"actions": data}},  # update
                )
            return Response(status=204)

    @app.route("/dc/enterRealTimeMode", methods=["POST"])
    def collectEnterRealTimeMode():
        """Handle data collection request for user entering real time mode.
            This request does not affect user's interaction with the app.
            Data is recorded only if user accepted the data collection policy.

        Returns:
            Empty REST response with appropriate status code.
        """
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if body:
            if find_user_by_token(body.get("token", None)) is None:
                return Response(status=401)
            data = {"api_call": "/dc/enterRealTimeMode", "timestamp": body["timestamp"]}
            if body["policy_accepted"]:
                db_sessions.update_one(
                    {"session_id": body["session_id"]},  # filter
                    {"$push": {"actions": data}},  # update
                )
            return Response(status=204)

    @app.route("/dc/enterDebuggerMode", methods=["POST"])
    def collectEnterDebuggerMode():
        """Handle data collection request for user entering debugger mode.
            This request does not affect user's interaction with the app.
            Data is recorded only if user accepted the data collection policy.

        Returns:
            Empty REST response with appropriate status code.
        """
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if body:
            if find_user_by_token(body.get("token", None)) is None:
                return Response(status=401)
            data = {"api_call": "/dc/enterDebuggerMode", "timestamp": body["timestamp"]}
            if body["policy_accepted"]:
                db_sessions.update_one(
                    {"session_id": body["session_id"]},  # filter
                    {"$push": {"actions": data}},  # update
                )
            return Response(status=204)

    @app.route("/dc/displayCircuit", methods=["POST"])
    def collectDisplayCircuit():
        """Handle data collection request sent when user displays a
            subcircuit visualization.
            This request does not affect user's interaction with the app.
            Data is recorded only if user accepted the data collection policy.

        Returns:
            Empty REST response with appropriate status code.
        """
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if body:
            if find_user_by_token(body.get("token", None)) is None:
                return Response(status=401)
            f = body["function"]
            f.pop("img", None)
            for c in f["children"]:
                c.pop("img", None)
                c.pop("children", None)

            data = {"api_call": "/dc/displayCircuit", "timestamp": body["timestamp"], "function": f}
            if body["policy_accepted"]:
                db_sessions.update_one(
                    {"session_id": body["session_id"]},  # filter
                    {"$push": {"actions": data}},  # update
                )
            return Response(status=204)

    @app.route("/dc/displayFuncInfo", methods=["POST"])
    def collectDisplayFuncInfo():
        """Handle data collection request sent when user displays a
            subcircuit information box.
            This request does not affect user's interaction with the app.
            Data is recorded only if user accepted the data collection policy.

        Returns:
            Empty REST response with appropriate status code.
        """
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if body:
            if find_user_by_token(body.get("token", None)) is None:
                return Response(status=401)
            f = body["function"]
            f.pop("img", None)
            for c in f["children"]:
                c.pop("img", None)
                c.pop("children", None)
            data = {
                "api_call": "/dc/displayFuncInfo",
                "timestamp": body["timestamp"],
                "function": f,
            }
            if body["policy_accepted"]:
                db_sessions.update_one(
                    {"session_id": body["session_id"]},  # filter
                    {"$push": {"actions": data}},  # update
                )
            return Response(status=204)

    @app.route("/bugreport", methods=["POST"])
    def bugreport():
        """Handle user sending a bug report via the in-app form

        Returns:
            Empty REST response with appropriate status code.
        """
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if body:
            if find_user_by_token(body.get("token", None)) is None:
                return Response(status=401)
            data = {
                "api_call": "/bugreport",
                "timestamp": body["timestamp"],
                "description": body["description"],
                "user_email": body["user_email"],
            }
            if body["policy_accepted"]:
                db_sessions.update_one(
                    {"session_id": body["session_id"]},  # filter
                    {"$push": {"actions": data}},  # update
                )
            db_bugs.insert_one(
                {
                    "token": body["token"],
                    "session_id": body["session_id"],
                    "timestamp": body["timestamp"],
                    "email": body["user_email"],
                    "description": body["description"],
                }
            )
        return Response(status=204)

    return app
