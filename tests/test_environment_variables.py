import os
import shutil
from kas import kas


def test_build_dir_is_placed_inside_work_dir_by_default(changedir, tmpdir):
    conf_dir = str(tmpdir.mkdir('test_env_variables'))
    shutil.rmtree(conf_dir, ignore_errors=True)
    shutil.copytree('tests/test_environment_variables', conf_dir)

    os.chdir(conf_dir)

    kas.kas(['checkout', 'test.yml'])

    assert(os.path.exists(os.path.join(os.getcwd(), 'build', 'conf')))


def test_build_dir_can_be_specified_by_environment_variable(changedir, tmpdir):
    conf_dir = str(tmpdir.mkdir('test_env_variables'))
    build_dir = str(tmpdir.mkdir('test_build_dir'))
    shutil.rmtree(conf_dir, ignore_errors=True)
    shutil.copytree('tests/test_environment_variables', conf_dir)
    shutil.rmtree(build_dir, ignore_errors=True)
    os.chdir(conf_dir)

    os.environ['KAS_BUILD_DIR'] = build_dir
    kas.kas(['checkout', 'test.yml'])
    del os.environ['KAS_BUILD_DIR']

    assert(os.path.exists(os.path.join(build_dir, 'conf')))
