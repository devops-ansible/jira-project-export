#!/usr/bin/env python3

###
## Helper function while development: python cli history
###
def history ( lineNumbers=True ):
  import readline
  if lineNumbers:
    formatstring = '{0:4d}  {1!s}'
  else:
    formatstring = '{1!s}'
  for i in range( 1, readline.get_current_history_length() + 1 ):
    print( formatstring.format( i, readline.get_history_item( i ) ) )

###
## fetch OK from user – y|n case insensitive
###
def confirm():
    answer = ""
    while answer not in ["y", "n"]:
        answer = input("Continue? [Y/N] ").lower()
    return answer == "y"

###
## prepare for ApiError usage
###
class APIError(Exception):
    """An API Error Exception"""
    def __init__(self, status):
        self.status = status
    def __str__(self):
        return "APIError: status={}".format(self.status)

###
## ensure that all requirements are installed and all directories exist
###
import os, sys, subprocess, json

subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
subprocess.check_call([sys.executable, '-m', 'pip'] + 'install -r requirements.txt'.split(), stdout=open(os.devnull, 'wb'))
subprocess.check_call(['apt-get', 'update'], stdout=open(os.devnull, 'wb'))
subprocess.check_call(['apt-get', 'upgrade', '-yq'], stdout=open(os.devnull, 'wb'))
print('installation of requirements finished ...')
print()

###
## fetch variables from ENV
###
from dotenv import load_dotenv
load_dotenv()

destination_url = os.getenv( "DOWNLOAD_URL", "http://localhost/jira" )
replace_users   = json.loads( os.getenv( "USER_MAPPING", "{}" ) )
jiraMaxIssues   = int( os.getenv( "X_MAX_ISSUES", 500 ) )

e_jira    = os.getenv( "X_JIRA_URL" )
e_user    = os.getenv( "X_JIRA_USER" )
e_cookies = os.getenv( "X_JIRA_COOKIES" )
e_pass    = os.getenv( "X_JIRA_PASS" )
e_prj     = os.getenv( "X_PROJECT_KEY" )
e_jql     = os.getenv( "X_CUSTOM_FILTER" )
e_quiet   = os.getenv( "X_QUIET" )

###
## ask user for relevant arguments if not already provided
###
import argparse
import getpass

parser = argparse.ArgumentParser()
parser.add_argument('-j', type=str, nargs='?', help='Jira URL')
parser.add_argument('-u', type=str, nargs='?', help='Username')
parser.add_argument('-p', type=str, nargs='?', help='Password')
parser.add_argument('-f', type=str, nargs='?', help='Filter / JQL instead of project')
parser.add_argument('-x', type=str, nargs='?', help='Project-Key of project to be exported')
parser.add_argument('-q', type=str, nargs='?', help='Quiet / Headless mode')

args   = parser.parse_args()

try:
    jira
except:
    if args.j != None:
        jira = args.j
    elif e_jira:
        jira = e_jira
    else:
        jira = input('Jira URL: ')

try:
    cookies
except:
    if e_cookies:
        cookies = json.loads( e_cookies )

try:
    username
except:
    if args.u != None:
        username = args.u
    elif e_user:
        username = e_user
    else:
        try:
            cookies
        except:
            username = input('Username: ')

try:
    password
except:
    if args.p != None:
        password = args.p
    elif e_pass:
        password = e_pass
    else:
        try:
            cookies
        except:
            password = getpass.getpass()

try:
    custom_filter
except:
    if args.f != None:
        custom_filter = args.f
    elif e_jql:
        custom_filter = e_jql
    else:
        custom_filter = False
        try:
            project
        except:
            if args.x != None:
                project = args.x
            elif e_prj:
                project = e_prj
            else:
                project = input('Project-Key of project to be exported: ')

try:
    quiet
except:
    if args.q != None:
        quiet = args.q
    elif e_quiet:
        quiet = e_quiet
    else:
        quiet = "False"

###
## In Non-Quiet-Mode ensure by shout out that the given user is permitted correctly
###
if quiet == 'False':

    ensure_project_rights = "Did you ensure, "

    try:
        ensure_project_rights += username
    except:
        ensure_project_rights += "your cookie given user "

    ensure_project_rights += "is permitted correctly within the project"

    try:
        project
        ensure_project_rights += ' “' + project + '”?'
    except:
        ensure_project_rights += 's of the given JQL?'

    blanks   = ' ' * ( len(ensure_project_rights) + 2 )
    nl_color = '\u001b[0m\n\u001b[0;1;93;41m'
    print('\u001b[0;1;93;41m' + blanks + nl_color + ' ' + ensure_project_rights + ' ' + nl_color + blanks + '\u001b[0m')
    blanks = ' ' * 56
    nl_color = '\u001b[0m\n\u001b[0;45;92m'
    print('\u001b[0;45;92m' + blanks + nl_color + ' The easiest way to ensure that is to put them in every ' + nl_color +' project role that does exist within the project(s).    ' + nl_color + blanks + '\u001b[0m')
    print()
    if (not confirm()):
        blanks = ' ' * 81
        nl_color = '\u001b[0m\n\u001b[0;1;93;41m'
        sys.exit('\n\u001b[0;1;93;41m' + blanks + nl_color +' OK, we\'ve to stop here for now. Please retry after you ensured the permissions. ' + nl_color + blanks + '\u001b[0m\n')

###
## preparing was successful, now start
###
import io, re, csv, requests
from bs4       import BeautifulSoup
from urllib    import parse
from datetime  import datetime
from pathlib   import Path

currentSession = requests.Session()
try:
    cookies
    fqdn = parse.urlparse( jira ).netloc
    for key, value in cookies.items():
        currentSession.cookies.set( key, value, domain=fqdn )
except:
    pass

def checkForLogin():
    resp = currentSession.get( jira )
    if resp.status_code != 200:
        raise APIError(resp.status_code)
    soup = BeautifulSoup(resp.content, 'html.parser')
    test = soup.find( class_ = re.compile( "login-link" ) )
    if test:
        login()
        checkForLogin()

def login():
    loginObject = {
        'os_username': username,
        'os_password': password,
        'os_destination': '',
        'user_role': '',
        'atl_token': '',
        'login': "Log In"
    }
    resp = currentSession.post( jira + '/login.jsp', data = loginObject )
    if resp.status_code != 200:
        raise APIError(resp.status_code)

def loginAndFetch(Url, method = 'get', data = {}, skipLogin = False):
    if not skipLogin:
        checkForLogin()
    if method == 'get':
        resp = currentSession.get  ( Url )
    else:
        resp = currentSession.post ( Url, data )
    if resp.status_code != 200:
        raise APIError ( resp.status_code )
    return resp

def checkJQL ( JQL, jqls = [] ):
    jqlUrl  = jira + '/issues/?jql=' + parse.quote( JQL )
    listUrl = jira + '/rest/issueNav/latest/preferredSearchLayout'

    # list-view has to be default – eventually the user has to interact
    defView = ''
    i = 0
    while defView != 'list-view':
        if i > 0:
            nl_color = '\u001b[0m\n\u001b[0;1;93;41m'
            hint1    = 'Currently, filter results are not displayed as a list but in detail. Please change.'
            hint2    = 'To do that, head to this url with the defined user and change on the top right side:'
            hintUrl  = jira + '/issues/?jql='
            length   = max( [ len( hint1 ), len( hint2 ), len( hintUrl ) ] )
            blanks   = ' ' * ( length + 2 )
            hint1    += ' ' * ( length - len( hint1 ) )
            hint2    += ' ' * ( length - len( hint2 ) )
            hintUrl  += ' ' * ( length - len( hintUrl ) )
            print('\u001b[0;1;93;41m' + blanks + nl_color + ' ' + hint1 + ' ' + nl_color + ' ' + hint2 + ' ' + nl_color + ' ' + hintUrl + ' ' + nl_color + blanks + '\u001b[0m')
            print()
            confirm()
        resp    = loginAndFetch( listUrl )
        defView = resp.content.decode( 'utf-8' )
        i += 1

    resp    = loginAndFetch( jqlUrl )
    soup    = BeautifulSoup( resp.content, 'html.parser' )
    test    = soup.find( class_ = re.compile( "results-count-total" ) )
    try:
        resultCount = int( test.text )
    except:
        resultCount = 0

    print()

    if resultCount >= jiraMaxIssues:
        pageLength = len( soup.find_all( class_ = re.compile( "issuerow" ) ) )
        startIndex = jiraMaxIssues - pageLength
        resp       = loginAndFetch( jqlUrl + '&startIndex=' + str( startIndex ))
        soup       = BeautifulSoup( resp.content, 'html.parser' )
        lastCount  = soup.find_all( class_ = re.compile( "issuekey" ) )
        lcissuekey = lastCount[ -1 ].text.strip()
        jqls.append( 'key <= ' + lcissuekey + ' AND ' + JQL )
        regex = 'key > .*? AND '
        JQL = re.sub( regex, '', JQL )
        jqls    = checkJQL( 'key > ' + lcissuekey + ' AND ' + JQL, jqls )
    elif resultCount > 0:
        jqls.append( JQL )
    return jqls

def downloadJQL ( JQL, cound_jql ):
    c_attach  = 0
    jqlUrl    = jira + '/sr/jira.issueviews:searchrequest-csv-all-fields/temp/SearchRequest.csv?jqlQuery=' + parse.quote( JQL )
    resp      = loginAndFetch( jqlUrl )
    csvstring = resp.content.decode("utf-8")
    for oldUser, replaceUser in replace_users.items():
        csvstring = re.sub('\[~' + oldUser + '\]', '[~' + replaceUser + ']', csvstring)
        csvstring = re.sub('(^|,)' + oldUser + '(,|$)', '\g<1>' + replaceUser + '\g<2>', csvstring)
    csvRows   = [ row for row in csv.reader( csvstring.splitlines(), delimiter=',' ) ]
    headers   = csvRows[0]
    csvRows.pop(0)
    csv2rowHeaders   = [ 'Attachment' ]
    # csv2rowHeaders   = [ 'Comment', 'Attachment' ]
    # nameCheckHeaders = [ 'Assignee', 'Reporter', 'Creator', 'Watchers' ]
    csv2rowIndices   = []
    attachmentIndices = []
    for csv2h in csv2rowHeaders:
        x = [ s for s, t in enumerate(headers) if t == csv2h ]
        csv2rowIndices = csv2rowIndices + x
        if csv2h == 'Attachment':
            attachmentIndices = x
    # nameCheckIndices = []
    # for csv2h in nameCheckHeaders:
    #     x = [ u for u, v in enumerate(headers) if v == csv2h ]
    #     nameCheckIndices = nameCheckIndices + x
    i = 0
    while i < len(csvRows):
        cRow = csvRows[i]
        # for k in nameCheckIndices:
        #     if cRow[k] in replace_users:
        #         csvRows[i][k] = replace_users[ cRow[k] ]
        for j in csv2rowIndices:
            try:
                specialRow = [ row for row in csv.reader( cRow[j].splitlines(), delimiter=';' ) ][0]
                # specialRow = list(csv.reader( cRow[j].splitlines(), delimiter=';' ))[0]
                # if specialRow[1] in replace_users:
                #     specialRow[1] = replace_users[ specialRow[ 1 ] ]
                if j in attachmentIndices:
                    dlUrlParts = parse.urlparse( specialRow[3] )
                    dlUrl      = jira + dlUrlParts.path
                    resp = loginAndFetch( dlUrl )
                    fileRoot, fileExt = os.path.splitext( dlUrlParts.path )
                    oldFileId = dlUrlParts.path.split('/')[3]
                    filePath = ('/attachments/' + project + '_' + oldFileId + fileExt).lower()
                    specialRow[3] = destination_url + filePath
                    dlPath = downloadBase + filePath
                    dlDir  = Path( dlPath ).parent
                    if not os.path.exists( dlDir ):
                        os.makedirs( dlDir )
                    with open( dlPath, 'wb' ) as f:
                        f.write(resp.content)
                    c_attach += 1
                output = io.StringIO()
                writer = csv.writer(output, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(specialRow)
                csvRows[i][j] = output.getvalue().strip()
                output.close()
            except:
                pass
        i += 1
    try:
        filename_start = project
    except:
        filename_start = 'custom'
    csv_name = ( filename_start + '_part-' + str( cound_jql ) + datetime.today().strftime('_%Y%m%d_%H%M%S') + '.csv' ).lower()
    with open( downloadBase + '/' + csv_name , 'w' ) as f:
        writer = csv.writer( f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL )
        writer.writerow( headers )
        writer.writerows( csvRows )
    print ('Finished downloading CSV file ' + csv_name + ' and ' + str( c_attach ) + ' corresponding attachments')

downloadBase = 'downloads'
if custom_filter != False:
    baseJQL  = custom_filter
else:
    baseJQL  = 'project = ' + project + ' ORDER BY key'

allJQLs      = checkJQL(baseJQL)

confirm_now_downloading = 'Checked the project and now starting to download CSV files for ' + str( len( allJQLs ) ) + ' JQL filter parts ...'
blanks   = ' ' * ( len(confirm_now_downloading) + 2 )
nl_color = '\u001b[0m\n\u001b[\033[1;42;97m'
print('\n\u001b[\033[1;42;97m' + blanks + nl_color + ' ' + confirm_now_downloading + ' ' + nl_color + blanks + '\u001b[0m\n')

c_jql = 0
for JQL in allJQLs:
    c_jql += 1
    downloadJQL( JQL, c_jql )

print()
