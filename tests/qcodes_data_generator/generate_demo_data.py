import time
from pathlib import Path
import numpy as np
import qcodes as qc

from qcodes.dataset import (
    Measurement,
    experiments,
    initialise_or_create_database_at,
    load_or_create_experiment,
)
from qcodes.instrument_drivers.mock_instruments import (
    DummyInstrument,
    DummyInstrumentWithMeasurement,
)

# %%
data_dir = Path(__file__).parent.parent / "test_data" / "qcodes_data"

print(f"Create database in {data_dir}")
initialise_or_create_database_at(
    data_dir / "qcodes_test.db"
)

# %%

# preparatory mocking of physical setup
dac = DummyInstrument("dac", gates=["ch1", "ch2"])
dmm = DummyInstrumentWithMeasurement("dmm", setter_instr=dac)
station = qc.Station(dmm, dac)

# %%
t_start = time.perf_counter()
exp = load_or_create_experiment(
    experiment_name="browser_demo", sample_name="no sample"
)

meas = Measurement(exp, name="demo")
meas.register_parameter(dac.ch1)  # register the first independent parameter
meas.register_parameter(dac.ch2)  # register the second independent parameter
meas.register_parameter(
    dmm.v2, setpoints=(dac.ch1, dac.ch2)
)  # register the dependent one
meas.register_parameter(
    dmm.v1, setpoints=(dac.ch1, dac.ch2)
)  # register the 2nd dependent parameter


# run a 2D sweep

with meas.run() as datasaver:
    for v1 in np.linspace(-1, 1, 200):
        for v2 in np.linspace(-1, 1, 201):
            dac.ch1(v1)
            dac.ch2(v2)
            val1 = dmm.v1.get()
            val2 = dmm.v2.get()
            datasaver.add_result(
                (dac.ch1, v1), (dac.ch2, v2), (dmm.v1, val1), (dmm.v2, val2)
            )

ds1 = datasaver.dataset

duration = time.perf_counter() - t_start
print("Duration", duration)


# %%

for exp in experiments():
    for ds in exp.data_sets():
        xds = ds.to_xarray_dataset()
        comp = {"compression": "gzip", "compression_opts": 9}
        encoding = {var: comp for var in list(xds.data_vars)+list(xds.coords)}
        xds.to_netcdf(data_dir / f"ds_{xds.attrs['run_id']}.hdf5", engine='h5netcdf', encoding=encoding)
