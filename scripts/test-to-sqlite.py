import sqlite3
import argparse
import os


def main():
    parser = argparse.ArgumentParser(description='MuDeeR')
    parser.add_argument('-d', '--dir', help='.wav files', nargs=1, required=True)
    args = parser.parse_args()

    data_dir = args.dir[0]

    conn = sqlite3.connect(data_dir + "/data.sqlite")
    c = conn.cursor()

    data_files = os.listdir(data_dir)
    wav_files = []

    for f in data_files:
        if f[-4:] == ".wav":
            wav_files.append(f)

    sql_data = []
    for w in wav_files:
        with open(data_dir + "/" + w + ".txt") as f:
            data = f.readline()
            sql_data.append((w, data, 0))

    # c.execute("""CREATE TABLE IF NOT EXISTS files (
    #     file TEXT PRIMARY KEY,
    #     text TEXT,
    #     corrected INTEGER
    #     );""")

    c.executemany('INSERT INTO files VALUES (?,?,?)', sql_data)

    # print(c.fetchone())

    # # # Create table

    # # # Insert a row of data
    # # c.execute("INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)")

    # # # Save (commit) the changes
    conn.commit()

    # # We can also close the connection if we are done with it.
    # # Just be sure any changes have been committed or they will be lost.
    conn.close()


if __name__ == "__main__":
    main()
