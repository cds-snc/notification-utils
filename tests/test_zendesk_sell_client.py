import requests_mock

from notifications_utils.clients.zendesk.zendesk_sell_client import ZenDeskSellClient
from notifications_utils.contact_request import ContactRequest


def test_create_lead(app):
    def match_json(request):
        expected = {
            'data': {
                'last_name': 'User',
                'first_name': 'Test',
                'organization_name': '',
                'email': 'test@email.com',
                'description': 'Program: \n: ',
                'tags': ["Support Request", "en"],
                'status': 'New',
                'custom_fields': {
                    'Product': ['Notify'],
                    'Source': 'Demo request form',
                    'Intended recipients': 'No value'
                }
            }
        }

        json_matches = request.json() == expected
        basic_auth_header = request.headers.get('Authorization') == f"Bearer zendesksell-api-key"

        return json_matches and basic_auth_header

    with requests_mock.mock() as rmock:
        rmock.request(
            "POST",
            url='https://example.com/zendesksell/v2/leads/upsert?email=test@email.com',
            headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
            additional_matcher=match_json,
            status_code=201
        )

        with app.app_context():
            # mock config
            app.config['ZEN_DESK_BASE_URL'] = 'https://example.com/zendesksell'
            app.config['ZEN_DESK_BASE_API_KEY'] = 'zendesksell-api-key'

            data = {'email_address': "test@email.com", 'name': 'Test User'}
            response = ZenDeskSellClient(app, ContactRequest(**data)).send_lead()
            assert response == 201


def test_create_lead_missing_name(app):
    with app.app_context():

        # mock config
        app.config['ZEN_DESK_BASE_URL'] = 'https://example.com/zendesksell'
        app.config['ZEN_DESK_BASE_API_KEY'] = 'zendesksell-api-key'

        try:
            response = ZenDeskSellClient(app, ContactRequest(**{'email_address': "test@email.com"})).send_lead()
        except Exception as e:
            assert isinstance(e, AssertionError)