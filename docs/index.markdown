---
layout: page
title: CollabyBot | Home
permalink: /
---
**CollabyBot** is a Discord bot developed to make collaboration easier for software development teams by giving them access to their GitHub repositories and Jira boards from their team's Discord server. To get started, install CollabyBot in your Discord server by clicking the link below.

[![Add CollabyBot to Discord](https://img.shields.io/badge/Add%20CollabyBot-Discord-0052CC?style=flat&logo=discordstatic/v1?message=CollabyBot&logo=discord&color=5865F2)](https://discord.com/login?redirect_to=%2Foauth2%2Fauthorize%3Fclient_id%3D1022914261086900255%26permissions%3D535260818496%26scope%3Dbot)

CollabyBot lets you perform actions in GitHub and Jira using Discord slash commands. GitHub-related commands start with **/github** and Jira-related commands start with **/jira**. Before you can use the commands, you will need to get an **OAuth** access token from both platforms using **/github auth** and **/jira auth**.

Once you've authorized with GitHub, use **/github repos add** to add a repository to your server's list of associated repositories. You can use other **/github** commands to subscribe channels to event notifications from tracked repositories, view and approve pull requests, and more.

After authorizing with Jira, use **/jira instance set** to associate your server with a Jira instance. Use **/jira** commands to a view a project's active sprint and manage issues.

For a full list of available commands, use **/commands**. For more detailed explanations of commands, see the user guide.
