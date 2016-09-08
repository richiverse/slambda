from json import dumps
import logging
import urllib

import credstash
import requests
from bs4 import BeautifulSoup

from chalice import Chalice

app = Chalice(app_name='confluence')
app.debug = False

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def _connect_confluence(JIRA_USERNAME, JIRA_PASSWORD, **kwargs):
    """Connect to confluence and return a session object with auth initialized."""
    user = JIRA_USERNAME
    password = JIRA_PASSWORD
    auth = (user, password)
    session = requests.Session()
    session.auth=auth
    return session

def _get_content(session, url, query):
    """return content from a session query."""
    params = {'queryString': query}
    response = session.get(url, params=params)
    if response.ok:
        return response.content
    else:
        return 'No results found for query %s.' % query

def _parse_content(content, content_index=157, link_index=5, **kwargs):
    soup = BeautifulSoup(content, 'html.parser')
    highlights = soup.find_all(attrs={'class': 'highlights'})
    formatted_highlights = ['{}'.format(h.text[:content_index].encode('utf-8').strip()) for h in highlights]
    links = soup.find_all(attrs={'class':'search-result-link visitable'})
    formatted_links = ['<https://{JIRA_CLIENT_URL}{href}|{title}>'.format(
        JIRA_CLIENT_URL=kwargs['JIRA_CLIENT_URL'],
        href=l.get('href'),
        title=l.text.encode('utf-8').strip())
        for l in links[:link_index]]
    return '\n\n'.join(['{} -> _{}_'.format(l[0],l[1]) for l in zip(formatted_links, formatted_highlights)])

    if formatted_links:
        return {
            "response_type": "in_channel",
            "text": str(zip(formatted_links, formatted_highlights)),
            }
    else:
        return 'Something went wrong.'

def _is_authenticated_slack(token, **kwargs):
    return token == kwargs['CONFLUENCE_SLACK_TOKEN']

def _greet(response_url, text='Fetching'):
    requests.post(response_url, data=dumps({'text': text}))

@app.route('/wiki/slack')
def query():
    json = app.current_request.query_params
    try:
        token = json.pop('token')
        response_url = json.pop('response_url')
    except KeyError:
        logger.info(json)
        logger.info('external request')
    logger.info(json)

    env = app.current_request.to_dict()['context']['stage']
    config = credstash.getAllSecrets(context={'env': env, 'app': 'confluence'})
    if not _is_authenticated_slack(token, **config):
        return {'text': 'Sorry, {} only works in Slack!'
                ''.format(json['command'])}

    cql = json['text']
    _greet(response_url)
    session = _connect_confluence(**config)
    url = ('https://{JIRA_CLIENT_URL}/wiki/dosearchsite.action'
           ''.format(**config))
    content = _get_content(session, url, cql)
    parsed_content = _parse_content(content, **config)
    result = ('{}\n\n*View all ->* {}?queryString={}\n\n^ /wiki {}'
              ''.format(parsed_content, url, urllib.quote_plus(cql), cql))
    payload = {"response_type": "in_channel", "text": result }
    requests.post(response_url, data=dumps(payload))
