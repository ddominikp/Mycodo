# coding=utf-8
import threading

from flask_babel import lazy_gettext

from mycodo.config import SQL_DATABASE_MYCODO
from mycodo.config_translations import TRANSLATIONS
from mycodo.databases.models import Actions
from mycodo.databases.utils import session_scope
from mycodo.actions.base_action import AbstractFunctionAction
from mycodo.utils.database import db_retrieve_table_daemon
from mycodo.utils.actions import which_controller

MYCODO_DB_PATH = 'sqlite:///' + SQL_DATABASE_MYCODO

ACTION_INFORMATION = {
    'name_unique': 'activate_controller',
    'name': f"{TRANSLATIONS['controller']['title']}: {TRANSLATIONS['activate']['title']}",
    'library': None,
    'manufacturer': 'Mycodo',
    'application': ['functions'],

    'url_manufacturer': None,
    'url_datasheet': None,
    'url_product_purchase': None,
    'url_additional': None,

    'message': lazy_gettext('Activate a controller.'),

    'usage': 'Executing <strong>self.run_action("{ACTION_ID}")</strong> will activate the selected Controller. '
             'Executing <strong>self.run_action("{ACTION_ID}", value={"controller_id": "959019d1-c1fa-41fe-a554-7be3366a9c5b"})</strong> will activate the controller with the specified ID.',

    'custom_options': [
        {
            'id': 'controller',
            'type': 'select_device',
            'default_value': '',
            'options_select': [
                'Input',
                'Math',
                'Function',
                'Conditional',
                'PID',
                'Trigger'
            ],
            'name': lazy_gettext('Controller'),
            'phrase': 'Select the controller to activate'
        }
    ]
}


class ActionModule(AbstractFunctionAction):
    """Function Action: Activate Controller."""
    def __init__(self, action_dev, testing=False):
        super().__init__(action_dev, testing=testing, name=__name__)

        # Initialize custom options
        self.controller_id = None

        # Set custom options
        action = db_retrieve_table_daemon(
            Actions, unique_id=self.unique_id)
        self.setup_custom_options(
            ACTION_INFORMATION['custom_options'], action)

        if not testing:
            self.try_initialize()

    def initialize(self):
        self.action_setup = True

    def run_action(self, message, dict_vars):
        try:
            controller_id = dict_vars["value"]["controller_id"]
        except:
            controller_id = self.controller_id

        self.logger.debug(f"Finding controller with ID {controller_id}")

        (controller_type,
         controller_object,
         controller_entry) = which_controller(controller_id)

        if not controller_entry:
            msg = f" Error: Controller with ID '{controller_id}' not found."
            message += msg
            self.logger.error(msg)
            return message

        message += f" Activate Controller {controller_id} ({controller_entry.name})."

        if controller_entry.is_activated:
            message += " Notice: Controller is already active!"
        else:
            with session_scope(MYCODO_DB_PATH) as new_session:
                mod_cont = new_session.query(controller_object).filter(
                    controller_object.unique_id == controller_id).first()
                mod_cont.is_activated = True
                new_session.commit()
            activate_controller = threading.Thread(
                target=self.control.controller_activate,
                args=(controller_id,))
            activate_controller.start()

        self.logger.debug(f"Message: {message}")

        return message

    def is_setup(self):
        return self.action_setup
