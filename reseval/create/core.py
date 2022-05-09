import json
import os
import shutil
import typing

import reseval


###############################################################################
# Create a subjective evaluation
###############################################################################


def create(
    config: typing.Union[str, bytes, os.PathLike],
    directory: typing.Union[str, bytes, os.PathLike],
    local: bool = False,
    production: bool = False,
    detach: bool = False) -> str:
    """Setup a subjective evaluation

    Args:
        config: The configuration file
        directory: The directory containing the files to evaluate
        local: Run subjective evaluation locally
        production: Deploy the subjective evaluation to crowdsource
            participants
        detach: If running locally, detaches the server process

    Returns:
        str: The name of the evaluation, as given in the configuration file
    """
    if local and production:
        raise ValueError('Cannot deploy production build locally')

    # Load configuration file
    cfg = reseval.load.config_from_file(config)
    name = cfg['name']

    if (reseval.EVALUATION_DIRECTORY / name).exists():
        raise ValueError(f'Evaluation {name} already exists')

    # Copy client and server to cache
    for path in reseval.ASSETS_DIR.rglob('*'):
        if path.is_dir():
            continue
        destination = reseval.CACHE / path.relative_to(reseval.ASSETS_DIR)
        destination.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy(path, destination)

    # Don't overwrite production data
    if not production:
        prod_file = reseval.EVALUATION_DIRECTORY / name / '.prod'
        if prod_file.exists():
            raise ValueError(
                f'Not overwriting results of evaluation {name}',
                 'which has been run in production')

    # Save configuration as json for the frontend to access
    with open(reseval.CLIENT_CONFIGURATION_FILE, 'w') as file:
        json.dump(cfg | {'local': local}, file, indent=4)

    # Create test
    test = reseval.test.get(cfg)(cfg, directory)

    # Create and save assignments
    with open(reseval.CLIENT_ASSIGNMENT_FILE, 'w') as file:
        json.dump(test.assign(cfg['random_seed']), file, indent=4)
        # MOS test requires deterministic conditions
    if test.__class__.__name__ == "MOS":
        with open(reseval.CLIENT_CONDITION_FILE, 'w') as file:
            json.dump(test.assign_conditions(cfg['random_seed']), file, indent=4)



    # Copy configuration file
    file = reseval.EVALUATION_DIRECTORY / name / 'config.yaml'
    file.parent.mkdir(exist_ok=True, parents=True)
    try:
        shutil.copyfile(config, file)
    except shutil.SameFileError:
        pass

    # Indicate if we're running local development
    local_file = reseval.EVALUATION_DIRECTORY / name / '.local'
    if local:
        local_file.touch()
    elif local_file.exists():
        local_file.unlink()

    try:

        # Create file storage and upload
        reseval.storage.create(cfg, directory, local)

        # If heroku is used for either the database or server, setup the app here
        if (not local and
            (cfg['server'] == 'heroku' or cfg['database'] == 'heroku')):
            reseval.app.heroku.create(cfg)

        # Create database
        reseval.database.create(cfg, test, local)

        # Create server
        url = reseval.server.create(cfg, local, detach=detach)

        # Launch crowdsourced evaluation
        reseval.crowdsource.create(cfg, url, local, production)

    except (Exception, KeyboardInterrupt) as exception:

        # Cleanup resources
        reseval.destroy(name, True)

        raise exception

    # Indicate that the evaluation has been run in production
    if production:
        prod_file = reseval.EVALUATION_DIRECTORY / name / '.prod'
        with open(prod_file, 'w') as file:
            pass

    # Return the evaluation name for, e.g., monitoring and analysis
    return name
