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

## License

This project is published unter [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) license.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.
