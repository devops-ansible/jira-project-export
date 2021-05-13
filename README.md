# Jira Project Export

Exporting Jira projects to migrate them to other instances is somehow tricky. Importing Attachments needs them to be available through a reachable URL – without a Jira login. So we need to download them.

Also the set of users (usernames) could change from instance A to B, so we need to adjust / remap the issues.

This Tool-Kit supports you with that task and within the following lines, we describe how it works.

## Running the tool

The tool is written in `Python` and `Docker`.

### Start container

To start it up, please run (on your terminal from within the project root directory)

```sh
docker-compose up -d
```

### Configuration

There are a few possibilities to configure your run.

#### `.env` file

The `.env` file can be copied from `.env.example` within `src/` Directory. There you can configure the following settings:

| ENV Variable | Default Value | Description |
| ------------ | ------------- | ----------- |
| `USER_MAPPING` | `{}` | JSON Dictionary with old usernames as keys and new usernames as value, so e.g. `{"old.user.1":"new.user.1","old.user.2":"new.user.2"}`.<br/> *Be aware, that a backslash `\` needs special escaping. A single `\` within an username has to be represented by 8 (!) of them, so `\\\\\\\\`!* |
| `DOWNLOAD_URL` | `http://localhost/jira` | URL under which the attachments will be available after the export. Should be changed accordingly! |
| `X_MAX_ISSUES` | `500` | Jira defaults to break with 1000 issues, so the value should be less or equal to that. Default size of pages in Jira is 50, so this number has to be devidable by 50. |
| `X_JIRA_URL` | - | See arguments below `-j` |
| `X_JIRA_USER` | - | See arguments below `-u` |
| `X_JIRA_PASS` | - | See arguments below `-p` |
| `X_JIRA_COOKIES` | – | Use this JSON String variable to define cookies to avoid the Jira login (so usage can replace `X_JIRA_PASS` or corresponding `-p`). |
| `X_PROJECT_KEY` | - | See arguments below `-x` |
| `X_CUSTOM_FILTER` | – | See arguments below `-f` |
| `X_QUIET` | – | See arguments below `-q` |
| `DATETIME_FORMAT` | `%d.%m.%Y %H:%M.%S` | Date-Time-Format (Python way) for time printouts |

#### Arguments on script execution

Another option to define configurations are runtime arguments.  
By these, you can override (some) settings from `.env` file – see comments below.  
**All arguments that are not defined (either in `.env` or as runtime argument) will enforce interactive input by the user!**

| Argument | Help | ENV override | possible values | default value | Description |
| -------- | ---- | ------------ | --------------- | ------------- | ----------- |
| `-j`     | Jira URL | `X_JIRA_URL` | String | – | Full URL (without trailing slash) of the Jira instance, the export project could be found. There something like `http://172.18.0.8:8080` or `https://jira.example.com` is valid. |
| `-u`     | Jira User | `X_JIRA_USER` | String | – | Username to export the project. User has to be permitted full access to the project to be exported, filter result default view set to `list-view` and language set to `English (United States)`. |
| `-p`     | Jira Password | `X_JIRA_PASS` | String | – | Password corresponding to `X_JIRA_USER` |
| `-x`     | Export Jira Project – Project Key | `X_PROJECT_KEY` | String | – | Jira Project Key to be exported |
| `-q`     | Quiet / Headless mode | – | Boolean (`True`, `1`) | `False` | There is a confirmation step if this parameter is not set to ensure, `X_JIRA_USER` has all permissions within the project `X_PROJECT_KEY`. |
| `-f`     | Filter / JQL instead of project | – | String | – | A (fully tested / working) JQL string instead of selecting projects by their key. **IMPORTANT:** please ensure your JQL to be ordered by issue keys, so the last part of the overall JQL has to be `ORDER BY key`. |

### Running the export

If you want the docker container to speak with Jira locally through Docker networks, you should add the container to the corresponding networks manually by `docker network connect networkname project_exporter`

When everything is configured well (at least `USER_MAPPING` and `DOWNLOAD_URL` have to be configured propperly), we now can run the export:

* interactive with user interaction:

```sh
docker exec -it project_exporter ./scraper.py
```

* quiet mode with no user interaction:

```sh
docker exec -it project_exporter ./scraper.py -j "http://178.18.0.34:8080" -u jira_user -p password -x TODO -q 1
```

* usage of an `.env` file with the environmental variables listed above can enable the quiet mode with the first command, too!

Finally, you'll find all downloaded data – attachments and CSV export – within the `downloads` directory.

### Running the import – Docker based on the Jira host

Let's think, you have your Jira deployed by using a Docker image, so as a Docker Container. The easiest way to import your exported data, is to use a run-of-the-mill webserver image and provide the variable `DOWNLOAD_URL="http://name-of-the-import-container"` while running the script above.

To run a webserver like that, you can simply follow this example – and run it from project root. Be aware to add your deployed webserver container to any of the networks, your Jira container is part of. Unless that, you may not be able to use the short-name variant mentioned above! *(We're using a dedicated `database` network for that case below.)*

```sh
docker run -d --rm -v $(pwd)/downloads:/var/www/html --network="database" --name "name-of-the-import-container" devopsansiblede/apache
```

## Usernames change from old instance to new instance

Sometimes, the usernames within old and new instances differ for reasons. The whole tool suggests that you already know them while running it above. If you do not know them, the export will not handle them and you have to do it after running the export.

To fix that, you can use these small Python snippets – our recommendation is, to stay within a Python Docker container to proceed:

### Retrive the usernames

Name your files `1.csv` to `x.csv` where `x` is a number greater than 1. Place these files within the folder `export` and run the script below – after you changed at least the `maxFile` variable.

*Probably you should also check, if there do exist more user fields, you can add to `directUserH` helper variable or some more sub-CSV-Fields to be handled like `Comments` or `Log Work` ...*

```py
import csv, json, re

maxFile = 4;

users = []
directUserH = [ "Assignee", "Reporter", "Creator", "Watchers" ]

for x in list( range( 1, maxFile + 1 ) ):
    csvstring = ""
    with open('export/' + str(x) + '.csv') as f:
        csvstring = f.read()
    csvRows   = [ row for row in csv.reader( csvstring.splitlines(), delimiter=',' ) ]
    headers   = csvRows.pop(0)
    userRE =  r'\[~(.*?)\]'
    users  += re.findall(userRE, csvstring)
    for row in csvRows:
        i = 0
        for h in headers:
            if h in directUserH:
                users += [ row[ i ] ]
            elif h == 'Log Work':
                if row[ i ] != '':
                    users += [ list(csv.reader( [ row[ i ] ] , delimiter=';' ))[0][-2] ]
                # do the things with log work
            elif h == 'Comment':
                if row[ i ] != '':
                    users += [ list(csv.reader( [ row[ i ] ] , delimiter=';' ))[0][1] ]
                # do the things with comments
            i += 1
    users = list(dict.fromkeys(users))

print( json.dumps( dict.fromkeys( users, '' ), sort_keys=True, indent=4 ) )
```

This will give you a JSON Dictionary with all old users as keys and empty strings as values.

As a next step remove all the users that remain the same and add the new usernames for those as values to the JSON dictionary, so the transformation can be successful.

**Adjust also the last comma, if you were deleting values ... invalid JSON cannot be handled below"**

### Replace the usernames

Now create the file `users.json` and paste your result from above. The file has to be a sibbling to `export` directory.

After that was done, you can proceed by this Python snippet:

```py
import csv, json, re, os

with open( 'users.json' ) as users_json:
    replace_users = json.load( users_json )

if not os.path.exists('import'):
    os.makedirs('import')

for x in list(range(1, 5)):
    csvstring = ""
    with open('export/' + str(x) + '.csv') as f:
        csvstring = f.read()
    for oldUser, replaceUser in replace_users.items():
        mentionRE = r'\[~' + oldUser + r'\]'
        csvValueRE = r'(^|,|;)(' + oldUser + r')(;|,|$)'
        csvstring = re.sub( mentionRE, '[~' + replaceUser + ']', csvstring)
        while re.search( csvValueRE, csvstring ):
            csvstring = re.sub( csvValueRE, r'\g<1>' + replaceUser + r'\g<3>', csvstring)
    with open( 'import/' + str(x) + '.csv' , 'w' ) as f:
        f.write( csvstring )
```

This snippet reads the JSON file (and bricks if the JSON is not valid!) and continues with the user replacement. After replacing the users within the CSV files, the export files will be placed within the `import` directory.


## License

This project is published unter [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) license.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.
