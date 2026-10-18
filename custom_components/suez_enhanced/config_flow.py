"""UI setup for SUEZ Enhanced."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from pysuez.suez_client import SuezClient
from .const import DOMAIN, CONF_COUNTER_ID

class SuezEnhancedConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            client = SuezClient(user_input[CONF_USERNAME], user_input[CONF_PASSWORD], None)
            try:
                await client._connect()
                counter_id = await client.find_counter()
                if not counter_id:
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(str(counter_id))
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title=str(counter_id), data={**user_input, CONF_COUNTER_ID: str(counter_id)})
            except Exception:
                errors["base"] = "cannot_connect"
            finally:
                await client.close_session()
        schema = vol.Schema({vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
