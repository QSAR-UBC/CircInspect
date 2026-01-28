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

from pymongo import MongoClient
from datetime import datetime
import argparse
import pprint

db_client = MongoClient("localhost", 27017)
db = db_client.circinspect
db_sessions = db.sessions
db_users = db.users
db_bugs = db.bugs


def countActions():
    """Count the total number of times an API call is called from any session
        by any user

    Returns:
        a list of API calls and their total counts
    """
    q = list(
        db_sessions.aggregate(
            [
                {"$unwind": "$actions"},
                {"$group": {"_id": "$actions.api_call", "count": {"$sum": 1}}},
            ]
        )
    )
    return q


def countActionLike(name):
    """Count API calls that have a path similar to the name argument across
    users and sessions

    Args:
        name (string): name of the API call to search for

    Returns:
        a list of session id - API call tuples and their counts.
    """
    q = list(
        db_sessions.aggregate(
            [
                {"$unwind": "$actions"},
                {
                    "$match": {"actions.api_call": {"$regex": "(?i).*" + name + ".*(?-i)"}}
                },  # find actions with the name matching part of api_call,
                # case-insensitive
                {
                    "$group": {
                        "_id": {"session": "$session_id", "call": "$actions.api_call"},
                        "count": {"$sum": 1},
                    }
                },  # group by both session and API call
            ]
        )
    )
    return q


def countActionSessionLike(name, session):
    """Count API calls in a subset of sessions

    Args:
        name (string): name of the API call to search for
        session (string): session id to search for

    Returns:
        a list of session id - API call tuples and their counts.
    """
    q = list(
        db_sessions.aggregate(
            [
                {"$unwind": "$actions"},
                {
                    "$match": {
                        "actions.api_call": {"$regex": "(?i).*" + name + ".*(?-i)"},
                        "session_id": {"$regex": "(?i).*" + session + ".*(?-i)"},
                    }
                },  # find actions with the part of name and session id matching,
                # case-insensitive
                {
                    "$group": {
                        "_id": {"session": "$session_id", "call": "$actions.api_call"},
                        "count": {"$sum": 1},
                    }
                },  # group by both session and API call
            ]
        )
    )
    return q


def computeSessionLength(session_id):
    """Compute the time spent in session and in different modes.

    Records the calculated data to the database entry for the session.
    If data is currently in database, uses the one in database instead
    of recomputing. Does not do anything if the session was not ended
    properly with a /dc/sessionExit call, and returns 0, 0, 0.

    Args:
        session_id (string): full or partial ID for the session

    Returns:
        Int, Int, Int:
            time spent in session in milliseconds
            time spent in debugger in milliseconds
            time spent in realtime mode in milliseconds
    """
    total_length, debugger_length, realtime_length = 0, 0, 0

    q = db_sessions.find_one({"session_id": {"$regex": "(?i).*" + session_id + ".*(?-i)"}})
    actions = q["actions"]
    if (
        actions[-1]["api_call"] != "/dc/sessionExit"
        and actions[-2]["api_call"] != "/dc/sessionExit"
    ):
        return 0, 0, 0
    total_length = actions[-1]["timestamp"] - actions[0]["timestamp"]

    isRealTimeMode = True  # NOTE: assumes app starts in real-time mode
    start = actions[0]["timestamp"]
    for a in actions:
        if a["api_call"] == "/dc/enterDebuggerMode":
            realtime_length += a["timestamp"] - start
            start = a["timestamp"]
            isRealTimeMode = False
        elif a["api_call"] == "/dc/enterRealTimeMode":
            debugger_length += a["timestamp"] - start
            start = a["timestamp"]
            isRealTimeMode = True

    if isRealTimeMode:
        realtime_length += actions[-1]["timestamp"] - start
    else:
        debugger_length += actions[-1]["timestamp"] - start

    db_sessions.update_one(
        {"session_id": {"$regex": "(?i).*" + session_id + ".*(?-i)"}},
        {
            "$set": {
                "session_length_ms": total_length,
                "debugger_length_ms": debugger_length,
                "realtime_length_ms": realtime_length,
            }
        },
    )
    return total_length, debugger_length, realtime_length


def getSession(session_id):
    """Get all data related to sessions that match the session_id

    Args:
        session_id (string): A session id or a part of it to search for

    Returns:
        a list of all sessions whose session IDs contain the session_id
    """
    qs = db_sessions.find({"session_id": {"$regex": "(?i).*" + session_id + ".*(?-i)"}})
    out = []
    for q in qs:
        if "session_length_ms" not in q:
            total_l, debugger_l, rt_l = computeSessionLength(q["session_id"])
            q["session_length_ms"] = total_l
            q["debugger_length_ms"] = debugger_l
            q["realtime_length_ms"] = rt_l
        q.pop("_id", None)
        out.append(q)
    return out


def generalInfo():
    """Get some general information related to the use of the application

    Returns:
        a dict of data related to application
    """
    data = {
        "date_utc": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "session_count": db_sessions.count_documents({}),
        "enter_debugger_count": 0,
        "enter_realtime_count": 0,
        "total_session_minutes": 0,
        "total_debugger_minutes": 0,
        "total_realtime_minutes": 0,
    }
    for a in countActions():
        if a["_id"] == "/dc/enterDebuggerMode":
            data["enter_debugger_count"] = a["count"]
        if a["_id"] == "/dc/enterRealTimeMode":
            data["enter_realtime_count"] = a["count"]

    q = list(
        db_sessions.aggregate(
            [
                {
                    "$project": {
                        "session_id": 1,
                        "session_length_ms": 1,
                        "debugger_length_ms": 1,
                        "realtime_length_ms": 1,
                    }
                }
            ]
        )
    )

    for d in q:
        if "session_length_ms" in d:
            data["total_session_minutes"] += d["session_length_ms"] / 60000
            data["total_debugger_minutes"] += d["debugger_length_ms"] / 60000
            data["total_realtime_minutes"] += d["realtime_length_ms"] / 60000
        else:
            total_l, debug_l, rt_l = computeSessionLength(d["session_id"])
            data["total_session_minutes"] += total_l / 60000
            data["total_debugger_minutes"] += debug_l / 60000
            data["total_realtime_minutes"] += rt_l / 60000
    return data


def main():
    """Run the admin application with required arguments. Running admin app
    without arguments prints the general information about the application.
    To learn more about possible arguments, run `python3 admin.py -h`

    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", help="specify an output file to write admin data")
    parser.add_argument("-s", "--session", help="specify a session id")
    parser.add_argument(
        "-c", "--count", action="store_true", help="specify whether to count API calls or not"
    )
    parser.add_argument("-cl", "--countlike", help="specify an API call name to count")
    args = parser.parse_args()

    out = ""
    if args.session and args.countlike:
        out = countActionSessionLike(args.countlike, args.session)
    elif args.session and args.count:
        out = countActionSessionLike("", args.session)
    elif args.session:
        out = getSession(args.session)
    elif args.countlike:
        out = countActionLike(args.countlike)
    elif args.count:
        out = countActions()
    else:
        out = generalInfo()

    if args.output is None:
        pprint.pp(out)
    else:
        with open(args.output, "x") as file:
            file.write(pprint.pformat(out))


if __name__ == "__main__":
    main()
