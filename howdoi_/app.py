from json import dumps
import logging

from chalice import Chalice
import credstash
from howdoi import howdoi as hdi
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)
app = Chalice(app_name='howdoi_')
app.debug = False

def _call_howdoi(query):
    parser = hdi.get_parser()
    args = vars(parser.parse_args(query.split(' ')))
    return hdi.howdoi(args)


def _process_text(text):
    """usage: howdoi [-h] [-p POS] [-a] [-l] [-c] [-n NUM_ANSWERS] [-C] [-v]
    [QUERY [QUERY ...]]

    instant coding answers via the command line

    positional arguments:
    QUERY                 the question to answer

    optional arguments:
    -h, --help            show this help message and exit
    -p POS, --pos POS     select answer in specified position (default: 1)
    -a, --all             display the full text of the answer
    -l, --link            display only the answer link
    -c, --color           enable colorized output
    -n NUM_ANSWERS, --num-answers NUM_ANSWERS
    number of answers to return
    -C, --clear-cache     clear the cache
    -v, --version         displays the current version of howdoi
    """
    return _call_howdoi(
        '{} -n5'.
        format(text.encode('utf-8').strip()))

def _format_text(text):
    return '```{}```'.format(text)

def _greet(response_url, text='Fetching'):
    requests.post(response_url, data=dumps({'text': text}))

def _is_authenticated_slack(token):
    env = app.current_request.to_dict()['context']['stage']
    return token == credstash.getSecret(
        'HOWDOI_SLACK_TOKEN',
        context={'env': env})

@app.route('/howdoi/slack')
def howdoi_slack():
    json = app.current_request.query_params
    token = json.pop('token')
    logger.info(json)

    if json.get('response_url') and 'slack' in json['response_url']:
        if not _is_authenticated_slack(token):
            logger.info('unauthenticated request')
            return {'text': 'Sorry, {} only works in Slack!'
                    ''.format(json['command'])}

        text = json['text']
        response_url = json['response_url']
        _greet(response_url)
        query_response = _process_text(text)
        formatted_response = _format_text(query_response)
        payload = {'response_type': 'in_channel','text': formatted_response}
        requests.post(response_url, data=dumps(payload))
        requests.post(response_url, data=dumps({'response_type': 'in_channel',
                      'text':'^ How do I {}?'.format(text)}))

@app.route('/howdoi/json')
def howdoi_json():
    json = app.current_request.query_params
    logger.info(json)
    text = json['text']
    query_response = _format_text(text)
    return dumps(query_response)

@app.route('/introspect')
def introspect():
    if app.debug:
        logger.info('introspection')
        return app.current_request.to_dict()
