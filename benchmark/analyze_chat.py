import re
import os
import argparse
import pandas as pd


def analyze_chat(filename):
    pattern = "(FAILED|OK|> Malformed response|#### Tests timed out).*"
    log = []
    with open(filename) as f:
        for line in f:
            m = re.match(pattern, line)
            if m:
                log.append(m.group(1))

    round = 0
    results = [{"Malformed": 0, "timeout": 0}, {"Malformed": 0, "timeout": 0}]
    for line in log:
        if line == "FAILED":
            results[round]["pass"] = False
            round += 1
        elif line == "OK":
            results[round]["pass"] = True
            round += 1
        elif line == "#### Tests timed out":
            results[round]["timeout"] += 1
            results[round]["pass"] = False
            round += 1
        # Malformed doesn't mark the end of a try
        elif line == "> Malformed response":
            results[round]["Malformed"] += 1

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", "-d", help="The chat log directory")
    parser.add_argument("--out", "-o", help="The output csv file", default="")
    args = parser.parse_args()

    results = []
    for subdir, dirs, files in os.walk(args.dir):
        if ".aider.chat.history.md" not in files:
            continue

        path = os.path.join(subdir, ".aider.chat.history.md")
        dirname = subdir.split("/")[-1]
        result = analyze_chat(path)
        row = {}
        row["testcase"] = dirname
        row["Malformed-1"] = result[0]["Malformed"]
        row["timeout-1"] = result[0]["timeout"]
        row["pass-1"] = result[0]["pass"]
        row["Malformed-2"] = result[1]["Malformed"]
        row["timeout-2"] = result[1]["timeout"]
        if "pass" in result[1]:
            row["pass-2"] = result[1]["pass"]
        else:
            row["pass-2"] = "None"

        results.append(row)

    df = pd.DataFrame(results)
    if args.out:
        df.to_csv(args.out, index=False)

    malformed_chats = (df["Malformed-1"] + df["Malformed-2"]).astype(bool).sum()
    malformed_1 = df["Malformed-1"].astype(bool).sum()
    malformed_2 = df["Malformed-2"].astype(bool).sum()
    
    timeout_chats = (df["timeout-1"] + df["timeout-2"]).astype(bool).sum()
    
    pass_1 = len(df[df["pass-1"] == True])
    pass_2 = len(df[df["pass-2"] == True])
    print("Malformed chats: {}".format(malformed_chats))
    print("Pass 1:          {}".format(pass_1))
    print("Pass 2:          {}".format(pass_2))
    print("Pass in total:   {}".format(pass_1 + pass_2))
    print("Timeout chats:   {}".format(timeout_chats))
    print()
    print()
    print("Malformed 1:     {}".format(malformed_1))
    print("Malformed 2:     {}".format(malformed_2))


if __name__ == "__main__":
    main()
