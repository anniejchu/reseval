import time

import rich
import rich.progress

import reseval


###############################################################################
# Monitor subjective evaluations
###############################################################################


def monitor(name=None, interval=120):
    """Monitor subjective evaluations"""
    # List evaluations
    names = (
        list(reseval.EVALUATION_DIRECTORY.glob('*'))
        if name is None else [name])

    # Get total samples for each evaluation
    configs = [reseval.load.config_by_name(name) for name in names]
    totals = [
        cfg['participants'] * cfg['samples_per_participant']
        for cfg in configs]

    # Setup monitoring display
    analyses = [
        reseval.results(name, reseval.EVALUATION_DIRECTORY / name)
        for name in names]

    # Render display and monitor
    content = displays(names, totals, analyses)
    with rich.progress.Live(content, refresh_per_second=.2) as live:

        # Monitor evaluations
        while True:

            # Iterate over evaluations
            for index, (name, total) in enumerate(zip(names, totals)):

                # Get current progress
                reseval.database.download(
                    name,
                    reseval.EVALUATION_DIRECTORY / 'tables')
                count = len(reseval.load.responses(name))

                # Update display if we have new results
                if count != analyses[index]['samples']:

                    # Get current statistics
                    analysis = reseval.results(
                        name,
                        reseval.EVALUATION_DIRECTORY / name)
                    analyses[index] = analysis

                    # Update display
                    live.update(displays(names, totals, analyses))

            # If we're monitoring a single evaluation and it is done, exit
            if (len(names) == 1 and
                analyses[0]['samples'] == total and
                not reseval.crowdsource.active(names[0])):
                break

            # Wait a while
            time.sleep(interval)


def display(name, total, analysis):
    """Format one evaluation for display"""
    grid = rich.progress.Table.grid()
    grid.add_column()

    # Format a table of statistics
    table = rich.progress.Table.grid(padding=(0, 2))
    table.add_column(justify='right')
    table.add_column(justify='center')
    table.add_column(justify='center')
    table.add_column(justify='right')
    table.add_row('total', str(total))
    table.add_row(str('samples'), str(analysis['samples']))
    for condition, items in analysis['conditions'].items():
        for i, (test, values) in enumerate(items.items()):
            for j, (key, val) in enumerate(values.items()):
                table.add_row(
                    condition if i == 0 and j == 0 else None,
                    test if j == 0 else None,
                    key,
                    str(val))

    # Create progress bar
    bar = rich.progress.Progress(
        rich.progress.BarColumn(),
        rich.progress.TextColumn(
            '[progress.percentage]{task.percentage:>3.0f}%'))

    # Add task to progress bar
    bar.add_task(name, total=total, completed=analysis['samples'])

    # Add table and bar to grid
    grid.add_row(bar)
    grid.add_row(table)

    # return table, bar
    return rich.panel.Panel(grid, title=name)


def displays(names, totals, analyses):
    """Format multiple evaluations for display"""
    displays = rich.progress.Table.grid()
    for name, total, analysis in zip(names, totals, analyses):
        displays.add_row(display(name, total, analysis))
    return displays


def format_stats(stats):
    """Format statistics for printing to a table"""
    result = ''
    for key, value in stats.items():
        result += f'{key} - {value}\n'
    return result[:-1]
