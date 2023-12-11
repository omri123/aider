
# aider is AI pair programming in your terminal

This is a fork of [aider](https://github.com/paul-gauthier/aider). I keep it up to date and experiment with new features. Hopefully, some of them will be merged back to the original repo.

## Features

- Edit conversation history with `/hist` and `/edit_history` commands
- Integration with vscode [context server extension](https://marketplace.visualstudio.com/items?itemName=omribloch.aider-context-server) allow adding read-only context items:
  - `/add \issue-<uri>`: Add an issue to the chat.
  - `/add \references-<symbol>`: Add a list of symbol references to the chat.
  - `/add \commit-<hash>`: Add commit info and content to the chat.
  - `/show <issue|references|commit>`: Show the content of a context item.
  - `/drop <issue|references|commit>`: Remove matching context item from the chat session.
