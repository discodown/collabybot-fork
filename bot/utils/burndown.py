from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt


def burndown(jira, issues):
    """
    Utility method used by the /sprint command for creating a burndown chart.

    First add up all the story points in the sprint, issue by issue. Then calculate
    how many points remain for each day in the sprint by comparing issue's resolution date
    to each date in the sprint's timespan. Plot the remaining points vs. date by storing them
    in a dictionary and plotting the line.

    Also plot the guideline by finding the slope that creates a linear decline from
    start to end of the sprint.

    Return the filename of the newly created burndown chart so that Discord can open it.

    :param jira: The instance of the Jira class being used by the /sprint command
    :param issues: Collection of sprint issues retrieved by the Jira class instance
    :return str: Filename of the newly created burndown chart
    """

    total_points = 0
    for i in issues:
        if i.raw['fields'].get('customfield_10026') is not None:
            total_points += int(i.raw['fields']['customfield_10026'])
        else:
            total_points += 0
        sprint_id = i.raw['fields']['customfield_10020'][0]['id']

    # Get start and end date of sprint
    sprint = jira.sprint(sprint_id)
    start = sprint.raw['startDate'].split('T')[0]
    end = sprint.raw['endDate'].split('T')[0]

    # Timespan of sprint
    date_range = pd.date_range(start=start, end=end, freq='D', inclusive='left')

    remaining_points = {}
    for d in date_range:
        remaining = total_points
        for i in issues:
            # TODO: Replace exception with if-else checking for a None story points custom field
            try:
                # Remove issue's story points from remaining if its resolution date
                # is before/on current date in sprint timespan
                if i.fields.resolutiondate.split('T')[0] <= d.strftime('%Y-%m-%d'):
                    if i.raw['fields'].get('customfield_10026') is not None:
                        remaining -= int(i.raw['fields']['customfield_10026'])
                    else:
                        remaining -= 0
            except AttributeError:
                pass
        remaining_points[d.strftime('%Y-%m-%d')] = int(remaining) # Put remaining points value in date/points dict

    slope = -total_points / (len(remaining_points.keys()) - 1)  # get slope of ideal pace for guideline (linear decline)

    # Create guideline
    guideline = {}
    for i, k in zip(range(0, len(remaining_points.keys())), remaining_points.keys()):
        guideline[k] = (slope * i) + total_points  # should be a straight line

    # Plot chart
    fig = plt.figure(figsize=(12, 4))
    plt.step(remaining_points.keys(), remaining_points.values(), 'r-', label='Remaining Story Points', where='post')
    plt.plot(guideline.keys(), guideline.values(), color='grey', label='Guideline')
    plt.xlim([min(remaining_points.keys()), max(remaining_points.keys())])
    plt.ylim([0, total_points + 1])
    plt.xlabel('Date')
    plt.ylabel('Story Points')
    plt.legend()
    plt.title('Burndown Chart for Sprint \"{0}\" '.format(sprint.raw['name']))
    plt.gcf().autofmt_xdate()
    # Create filename using current date
    filename = 'burndown-' + datetime.now().strftime('%Y-%m-%d') + '-' + str(sprint.raw['id']) + '.jpg'
    # Save the plot locally
    plt.savefig(filename)
    # Return the filename
    return filename
