# Privacy and Local Data

AI Collaboration records coding-agent activity on the local machine. It does not send captured data to a network service.

## Storage

The default data directory is `~/.ai-collaboration`. Directory permissions are set to owner-only (`0700`) and the SQLite database and object files to owner read/write (`0600`) where the platform supports POSIX permissions.

Set `AI_COLLABORATION_HOME` for every agent host to relocate the shared store. A shared value is required for cross-host continuity.

## Redaction

Before persistence, the capture layer recursively redacts values whose keys resemble:

- API keys and tokens
- authorization and cookies
- credentials and passwords
- secrets and private keys

It also replaces bearer-token values and PEM private-key blocks found in strings.

Redaction is defense in depth, not a guarantee. Tool arguments, prompts, file content, command output, and unconventional credential names can still contain sensitive information. Do not enable passive capture in repositories whose policy prohibits local activity logging.

## Retention

Version 0.1 stores history until the user removes the configured data directory. The plugin does not silently expire or upload records. Back up or delete that directory according to the repository's data-handling policy.

Before deleting, confirm the resolved location with:

```bash
bin/ai-collaboration doctor
```

Deletion is intentionally not exposed as an MCP tool so an agent cannot erase history through a routine tool call.

## Trust

Lifecycle hooks execute local Python code with the permissions of the host agent. Review the hook configuration and source before trusting the plugin. Codex and other hosts may require an explicit hook-trust decision; that security boundary should remain enabled.
