"""
Mandate Gateway — Unit Tests for Configuration & Settings Architecture
Section S00.3 — Security & Configuration Hardening
"""

import unittest
from apps.api.config import (
    ConfigurationError,
    Environment,
    LogLevel,
    SecretString,
    Settings,
    get_settings,
    reset_settings_cache,
)


class TestConfiguration(unittest.TestCase):

    def setUp(self) -> None:
        reset_settings_cache()

    def tearDown(self) -> None:
        reset_settings_cache()

    def test_valid_development_config_loading(self) -> None:
        env = {
            "APP_ENV": "development",
            "APP_NAME": "test-gateway",
            "LOG_LEVEL": "DEBUG",
            "HOST_CONTEXT": "false",
            "POSTGRES_HOST": "postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "mandate_gateway_dev",
            "POSTGRES_USER": "dev_user",
            "POSTGRES_PASSWORD": "dev_password_123",
            "REDIS_HOST": "redis",
            "REDIS_PORT": "6379",
            "REDIS_DB": "1",
        }
        settings = Settings.from_env(env_dict=env)

        self.assertEqual(settings.app_env, Environment.DEVELOPMENT)
        self.assertEqual(settings.app_name, "test-gateway")
        self.assertEqual(settings.log_level, LogLevel.DEBUG)
        self.assertFalse(settings.host_context)
        self.assertEqual(settings.postgres_host, "postgres")
        self.assertEqual(settings.postgres_port, 5432)
        self.assertEqual(settings.postgres_db, "mandate_gateway_dev")
        self.assertEqual(settings.postgres_user, "dev_user")
        self.assertEqual(settings.postgres_password.get_secret_value(), "dev_password_123")
        self.assertEqual(settings.redis_host, "redis")
        self.assertEqual(settings.redis_port, 6379)
        self.assertEqual(settings.redis_db, 1)

    def test_valid_test_environment_config(self) -> None:
        env = {
            "APP_ENV": "test",
            "HOST_CONTEXT": "true",
            "POSTGRES_HOST": "127.0.0.1",
            "REDIS_HOST": "127.0.0.1",
        }
        settings = Settings.from_env(env_dict=env)

        self.assertEqual(settings.app_env, Environment.TEST)
        self.assertTrue(settings.host_context)
        self.assertEqual(settings.postgres_host, "127.0.0.1")
        self.assertEqual(settings.redis_host, "127.0.0.1")

    def test_invalid_app_env_raises_configuration_error(self) -> None:
        env = {"APP_ENV": "invalid_environment"}
        with self.assertRaises(ConfigurationError) as cm:
            Settings.from_env(env_dict=env)
        self.assertIn("Invalid APP_ENV: 'invalid_environment'", str(cm.exception))

    def test_invalid_log_level_raises_configuration_error(self) -> None:
        env = {"LOG_LEVEL": "VERBOSE"}
        with self.assertRaises(ConfigurationError) as cm:
            Settings.from_env(env_dict=env)
        self.assertIn("Invalid LOG_LEVEL: 'VERBOSE'", str(cm.exception))

    def test_invalid_port_raises_configuration_error(self) -> None:
        env_high = {"POSTGRES_PORT": "99999"}
        with self.assertRaises(ConfigurationError) as cm:
            Settings.from_env(env_dict=env_high)
        self.assertIn("Invalid POSTGRES_PORT: '99999'", str(cm.exception))

        env_neg = {"POSTGRES_PORT": "-5"}
        with self.assertRaises(ConfigurationError) as cm:
            Settings.from_env(env_dict=env_neg)
        self.assertIn("Invalid POSTGRES_PORT: '-5'", str(cm.exception))

    def test_redis_db_non_negative_validation(self) -> None:
        # Valid DB indexes (0, 16, 100)
        env_valid_0 = {"REDIS_DB": "0"}
        s0 = Settings.from_env(env_dict=env_valid_0)
        self.assertEqual(s0.redis_db, 0)

        env_valid_100 = {"REDIS_DB": "100"}
        s100 = Settings.from_env(env_dict=env_valid_100)
        self.assertEqual(s100.redis_db, 100)

        # Invalid negative DB index
        env_neg = {"REDIS_DB": "-1"}
        with self.assertRaises(ConfigurationError) as cm:
            Settings.from_env(env_dict=env_neg)
        self.assertIn("Invalid REDIS_DB: '-1'", str(cm.exception))

    def test_empty_postgres_db_or_user_raises_configuration_error(self) -> None:
        env_empty_db = {"POSTGRES_DB": "  "}
        with self.assertRaises(ConfigurationError) as cm:
            Settings.from_env(env_dict=env_empty_db)
        self.assertIn("POSTGRES_DB cannot be empty", str(cm.exception))

        env_empty_user = {"POSTGRES_USER": ""}
        with self.assertRaises(ConfigurationError) as cm:
            Settings.from_env(env_dict=env_empty_user)
        self.assertIn("POSTGRES_USER cannot be empty", str(cm.exception))

    def test_production_mode_fails_fast_on_default_password(self) -> None:
        env = {
            "APP_ENV": "production",
            "POSTGRES_PASSWORD": "CHANGE_ME_LOCAL_ONLY",
        }
        with self.assertRaises(ConfigurationError) as cm:
            Settings.from_env(env_dict=env)
        self.assertIn(
            "POSTGRES_PASSWORD must be explicitly set to a secure value in production",
            str(cm.exception),
        )

    def test_container_mode_prohibits_localhost_hostname(self) -> None:
        env = {
            "APP_ENV": "development",
            "HOST_CONTEXT": "false",
            "POSTGRES_HOST": "localhost",
        }
        with self.assertRaises(ConfigurationError) as cm:
            Settings.from_env(env_dict=env)
        self.assertIn(
            "POSTGRES_HOST cannot be 'localhost' in container environment",
            str(cm.exception),
        )

    def test_secret_string_redaction_and_equality(self) -> None:
        secret = SecretString("super_secret_password_99")

        self.assertEqual(secret.get_secret_value(), "super_secret_password_99")
        self.assertEqual(str(secret), "[REDACTED]")
        self.assertEqual(repr(secret), "SecretString('[REDACTED]')")

        # Test equality
        self.assertEqual(secret, "super_secret_password_99")
        self.assertEqual(secret, SecretString("super_secret_password_99"))
        self.assertNotEqual(secret, "wrong_password")

    def test_settings_redaction(self) -> None:
        env = {
            "POSTGRES_PASSWORD": "my_super_secret_pass",
        }
        settings = Settings.from_env(env_dict=env)

        dict_redacted = settings.to_dict(redact=True)
        self.assertEqual(dict_redacted["POSTGRES_PASSWORD"], "[REDACTED]")

        repr_str = repr(settings)
        self.assertNotIn("my_super_secret_pass", repr_str)
        self.assertIn("[REDACTED]", repr_str)

    def test_get_settings_cached_singleton(self) -> None:
        env = {"APP_NAME": "singleton-test-app"}
        s1 = Settings.from_env(env_dict=env)
        self.assertEqual(s1.app_name, "singleton-test-app")
        reset_settings_cache()
        # Verify cache works
        s2 = get_settings()
        self.assertIsNotNone(s2)


if __name__ == "__main__":
    unittest.main()
