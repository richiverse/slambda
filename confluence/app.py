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

def _add_params(query, space=None, typ='page'):
    params = {'queryString': query,
              'cql':'type="{typ}" and siteSearch ~ "{query}"'.format(
                  typ=typ, query=query.replace('"','\\"'))}
    if space:
        params.update({'cql': '{} and space = "{}"'.format(
            params['cql'], space)})
    return params

def _get_content(session, url, params):
    """return content from a session query."""
    response = session.get(url, params=params)
    if response.ok:
        return response.content
    else:
        return 'No results found for query %s.' % str(params)

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

    _greet(response_url)
    cql = json['text']
    config = credstash.getAllSecrets(context={'env': 'dev', 'app': 'confluence'})

    result = _process(cql, **config)
    payload = dumps({"response_type": "in_channel", "text": result })
    requests.post(response_url, data=payload)

def _process(cql, **config):
    session = _connect_confluence(**config)
    url = ('https://{JIRA_CLIENT_URL}/wiki/dosearchsite.action'
           ''.format(**config))
    add_params = _add_params(cql, space=config.get('SPACE'))
    content = _get_content(session, url, add_params)
    parsed_content = _parse_content(content, **config)
    result = ('{}\n\n*View all ->* {}?{}\n\n^ /wiki {}'
              ''.format(parsed_content, url, urllib.urlencode(add_params), cql))
    return result

if __name__ == '__main__':
    import sys
    cql = sys.argv[1]
    config = credstash.getAllSecrets(context={'env': 'dev', 'app': 'confluence'})
    result = _process(cql, **config)
    print(result)
