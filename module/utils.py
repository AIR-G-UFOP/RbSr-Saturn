from module.core import *


def get_unique_name(name_links, log_names):
    if name_links:
        return [name for name, value in name_links.items() if value in log_names]
    else:
        return log_names


def get_log_name(name_links, unique_names, log):
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
