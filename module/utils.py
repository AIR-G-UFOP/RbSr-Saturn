from module.core import *


def get_unique_name(name_links, log_names):
    """
    name_links: dict correlating mass spec file names and laser log names
    unique_names: list holding log names to be converted to laser unique names
    """

    if name_links:
        return [name for name, value in name_links.items() if value in log_names]
    else:
        return log_names


def get_log_name(name_links, unique_names, log):
    """
    name_links: dict correlating mass spec file names and laser log names
    unique_names: list holding unique names to be converted to laser log names
    log: dict holding the laser log name and the order in which each file was analysed
    """

    if name_links:
        log_names = [name_links[name] for name in unique_names]
        order = {v: k for k, v in log.items()}
        return sorted(log_names, key=lambda x: order[x])
    else:
        return unique_names


def remap_dicts(data, link):
    if link:
        return {actual_key: data[past_key] for past_key, actual_key in link.items() if past_key in data}
    else:
        return data


def remap_dataframe(data, link):
    if link:
        return data.rename(index=link)
    else:
        return data
