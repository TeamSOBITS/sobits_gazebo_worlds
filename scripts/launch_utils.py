import os

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory


def build_gz_resource_path(package_share):
    model_paths = [
        os.path.join(package_share, 'models'),
    ]

    # Human models (walking actors and static poses) live in gz_human_sim.
    try:
        model_paths.append(
            os.path.join(get_package_share_directory('gz_human_sim'), 'models')
        )
    except PackageNotFoundError:
        pass

    # Source-checkout fallback: find sibling tmc_wrs_gz source tree
    src_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    tmc_source_models = os.path.join(src_root, 'tmc_wrs_gz', 'tmc_wrs_gz_worlds', 'models')
    if os.path.isdir(tmc_source_models):
        model_paths.append(tmc_source_models)

    for package_name in ('tmc_wrs_gz_worlds',):
        try:
            pkg_models = os.path.join(get_package_share_directory(package_name), 'models')
            if pkg_models not in model_paths:
                model_paths.append(pkg_models)
        except PackageNotFoundError:
            pass

    current_path = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    if current_path:
        model_paths.append(current_path)

    return os.pathsep.join(model_paths)
