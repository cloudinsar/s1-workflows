import logging

from testutils import *

_log = logging.getLogger(__name__)


@pytest.mark.skip(reason="TODO: Log into openEO backend")
def test_insar_coherence_against_openeo_backend(auto_title):
    import openeo

    url = "https://openeo.dataspace.copernicus.eu"
    connection = openeo.connect(url).authenticate_oidc()

    datacube = connection.datacube_from_process(
        process_id="insar_coherence",
        InSAR_pairs=[["2018-01-28", "2018-02-03"]],
        burst_id=249435,
        polarization="vv",
        sub_swath="IW2",
        # Coherence window size:
        coherence_window_rg=10,
        coherence_window_az=2,
        # Multillok parameters:
        n_rg_looks=4,
        n_az_looks=1,
    )

    datacube = datacube.save_result(format="GTiff")

    job = datacube.create_job(title=auto_title)
    job.start_and_wait()
    job.get_results().download_files("tmp" + auto_title)
