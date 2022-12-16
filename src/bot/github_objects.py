class Commit:
    def __init__(self, commit_message, action, repo, timestamp, url, user):
        self.commit_message = commit_message
        self.action = action
        self.repo = repo
        self.date = timestamp.split('T')[0]
        self.time = timestamp.split('T')[1][0:-1]
        self.url = url
        self.user = user

        # To Do: Check if proper format

    def object_string(self):
        """
        Triggered in each object handler. Formats a string to send to the bot.

        :return str: String format of the object and its notification message.
        """

        notify_message = F'Repository: {self.repo}\nCommit Message: {self.commit_message}\nDate: {self.date}\n' \
                         F'Time: {self.time}\nAuthor: {self.user}\nURL: {self.url}'
        return notify_message


class Issue:
    def __init__(self, body, action, repo, timestamp, url, user):
        self.body = body
        self.action = action
        self.repo = repo
        self.date = timestamp.split('T')[0]
        self.time = timestamp.split('T')[1][0:-1]
        self.url = url
        self.user = user
        # To Do: Check if proper format

    def object_string(self):
        """
        Triggered in each object handler. Formats a string to send to the bot.

        :return str: String format of the object and its notification message.
        """

        notify_message = F'Repository: {self.repo}\nIssue {self.action}\nIssue Body: {self.body}\nDate: {self.date}\n' \
                         F'Time: {self.time}\nAuthor: {self.user}\nURL: {self.url}'
        return notify_message


class PullRequest:
    def __init__(self, action, body, repo, timestamp, url, user, reviewer_requested, reviewer, review_body, pr_state):
        self.action = action
        self.body = body
        self.repo = repo
        self.date = timestamp.split('T')[0]
        self.time = timestamp.split('T')[1][0:-1]
        self.url = url
        self.user = user
        self.reviewer_requested = reviewer_requested
        self.reviewer = reviewer
        self.review_body = review_body
        self.pr_state = pr_state

    def object_string(self):
        """
        Triggered in each object handler. Formats a string to send to the bot.

        :return str: String format of the object and its notification message.
        """

        if self.action != 'review_requested' and self.reviewer is None:
            notify_message = F'Repository: {self.repo}\nPull Request {self.action}\n' \
                             F'Pull Request Description: {self.body}\nDate: {self.date}\nTime: {self.time}\n' \
                             F'User: {self.user}\nURL: {self.url}'
            return notify_message
        if self.reviewer is not None:
            notify_message = F'Repository: {self.repo}\nPull Request {self.action}\n{self.reviewer} wrote a Review\n' \
                             F'Body: {self.review_body}\nStatus: {self.pr_state}\nDate: {self.date}\n' \
                             F'Time: {self.time}\nURL: {self.url}'
            return notify_message
        if self.action == 'review_requested':
            notify_message = F'Repository: {self.repo}\nPull Request {self.action}\n' \
                             F'Reviewer Requested: {self.reviewer_requested}\nDescription: {self.body}\n' \
                             F'Date: {self.date}\nTime: {self.time}\nAuthor: {self.user}\nURL: {self.url}'
            return notify_message
