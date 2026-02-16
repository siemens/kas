.. note::
  When using |AWS_CONFIG_SOURCE| the entire content of ``~/.aws/sso/cache``
  directory is copied into the kas workspace. This might expose all active
  user sessions, including those not defined in the ``AWS_CONFIG_FILE``.
  To mitigate security risks, log out of unnecessary profiles before
  starting a build or use a separate system account to run the build.
