---
layout: page
title: CollabyBot | User Guide - Commands
permalink: /guide/commands/
show_sidebar: false
menubar: menu
---

## General Commands

* **/ping**: Simple way to test if the bot is online. Responds with "Pong."
* **/commands**: Get a paginated list of bot commands.

## Github Commands

* **/github**
    * **/github auth**: Authorize GitHub to access the GitHub API on your behalf using GitHub. CollabyBot will DM you a link directing you to the authorization page. After you complete the authorization process, CollabyBot will have an OAuth token for your account that lasts one year.
    * **/github repos**: Get a list of repositories currently tracked by your Discord server.
    * **/github repo**:
      * **/github repo add \<REPO OWNER>/\<REPO NAME>**: Add a GitHub repo to your server's list of tracked repos. Since this will create webhooks in the repository settings, the person using the command must have admin permissions for the repository. You can add as many repos as you like. If the webhooks already exist (probably because another server already added the repo), it will still be added to your server's repo list. Requires OAuth token.
      * **/github repo remove \<REPO OWNER>/\<REPO NAME>**: Remove a repo from your server's list of tracked repos. This will _not_ delete the webhooks from the repository's settings, which must be done manually on GitHub.
    * **/github subscribe**:
      * **/github subscribe issues \<REPO OWNER>/\<REPO NAME>**: Subscribe the current channel to notifications for issue events in a repo. The repo must be added using **/github repo add** before you can subscribe to notifications.
      * **/github subscribe pull-requests \<REPO OWNER>/\<REPO NAME>**: Subscribe the current channel to notifications for pull request events in a repo. The repo must be added using **/github repo add** before you can subscribe to notifications.
      * **/github subscribe commits \<REPO OWNER>/\<REPO NAME> \[BRANCH]**: Subscribe the current channel to notifications for commit events in a repo. If the BRANCH parameter is omitted, then CollabyBot will subscribe to events in all branches. The repo must be added using **/github repo add** before you can subscribe to notifications.
    * **/github unsubscribe**:
      * **/github unsubscribe issues \<REPO OWNER>/\<REPO NAME>**: Unsubscribe the current channel from notifications for issue events in a repo. This will _not_ remove the repo from the server.
      * **/github unsubscribe pull-requests \<REPO OWNER>/\<REPO NAME>**: Unsubscribe the current channel from notifications for pull request events in a repo. This will _not_ remove the repo from the server.
      * **/github unsubscribe commits \<REPO OWNER>/\<REPO NAME> \[BRANCH]**: Unsubscribe the current channel from notifications for commit events in a repo. If the BRANCH parameter is omitted, then CollabyBot will unsubscribe from events in all branches. This will _not_ remove the repo from the server.
    * **/github fetch**:
      * **/github fetch pull-requests \<REPO_OWNER>/\<REPO NAME**>: Get a list of open pull requests in a repository. The repo must be added using **/github repo add** first. Requires an OAuth token.
      * **/github fetch issues \<REPO_OWNER>/\<REPO NAME>**: Get a list of open issues in a repository. The repo must be added using **/github repo add** first. Requires an OAuth token.
    * **/github pull-request**:
      * **/github pull-request approve \<REPO_OWNER>/\<REPO NAME> \<PR NUMBER> \[COMMENT]**: Approve an open pull request in a repository. The repo must be added using **/github repo add** first. COMMMENT argument is optional. Requires OAuth token.
    * **/github issue**:
      * **/github issue assign \<REPO_OWNER>/\<REPO NAME> \<ISSUE NUMBER> \<ASSIGNEE(S)>**: Assign an issue to users in GitHub. The repo must be added using **/github repo add** first. ASSIGNEE(S) argument can be one or several users, separated by spaces in the latter case. Requires OAuth token.
      * **/github issue close \<REPO_OWNER>/\<REPO NAME> \<ISSUE NUMBER>**: Close an open issue in a repository. The repo must be added using **/github repo add** first. Requires OAuth token.

## Jira Commands

* **/jira**:
  * **/jira auth**:
  * **/jira instance**:
    * **/jira instance set \<INSTANCE>**: Set your server's associated Jira instance. You can only set one instance at a time. Instance argument should be the name of the instance (i.e. the part that proceeds _.atlassian.net_ in the URL). The instance must be within the scope of the OAuth token of the user sending the command. If an instance is already set, you will be asked if you want to change it. Requires OAuth token.
    * **/jira instance remove**: Reset the server's associated instance to none.
  * **/jira issue**:
    * **/jira issue get \<ISSUE ID>**: Get a summary of an issue in your server's Jira instance.
    * **/jira issue assign \<ISSUE ID> \<ASSIGNEE>**: Assign an issue to a user in Jira. ASSIGNEE argument can be wither a display name or a Jira account ID. If the ASSIGNEE argument is omitted, CollabyBot will respond with a list of assignable users (i.e. users with access to the issue's project) and their account IDs. If the issue has already been assigned, you will be asked if you want to reassign it. Requires OAuth token.
    * **/jira issue unassign \<ISSUE ID>**: Unassign an issue in Jira. Requires OAuth token.
  * **/jira sprint \<PROJECT ID>**: Get a summary of a project's active sprint, which includes a paginated list of issues and a burndown chart showing your teams progress. If the PROJECT ID argument is omitted, CollabyBot will respond with a list of available projects in your instance which includes both their names and project IDs. Requires OAuth token.