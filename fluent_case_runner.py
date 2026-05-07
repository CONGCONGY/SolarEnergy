"""PyFluent orchestration for the external ANSYS Fluent simulation workflow.

This module configures and runs Fluent. It does not reimplement CFD,
turbulence, or heat-transfer physics in Python. The visible setup already
orchestrates the paper-backed RNG k-epsilon model, energy equation, water
material, inlet condition, wall heat flux, and case-data output. Enhanced wall
treatment and GCI verification remain external Fluent/validation details that
should be changed only after the exact PyFluent setting or workflow is
confirmed.
"""

import ansys.fluent.core as pyfluent
import os
import time

DEFAULT_CASE_OUTPUT_DIR = r"E:\topoOptimization\DataResult"


def fluentcompute(path, number, output_dir=DEFAULT_CASE_OUTPUT_DIR):
    """Run Fluent meshing and solver setup for one PMDB geometry file."""
    if not path or not os.path.isfile(path):
        raise FileNotFoundError(f"PMDB geometry file does not exist: {path}")
    if not output_dir:
        raise ValueError("A Fluent case-data output directory is required.")
    os.makedirs(output_dir, exist_ok=True)

    meshing_session = pyfluent.launch_fluent(precision="double", processor_count=36, ui_mode="gui", mode="meshing")

    workflow = meshing_session.workflow
    meshing = meshing_session.meshing

    import_filename = path

    workflow.InitializeWorkflow(WorkflowType=r'Watertight Geometry')
    workflow.TaskObject['Import Geometry'].Arguments.set_state({r'FileName': import_filename,r'ImportCadPreferences': {r'MaxFacetLength': 0,},r'LengthUnit': r'mm',})
    workflow.TaskObject['Import Geometry'].Execute()

    workflow.TaskObject['Add Local Sizing'].AddChildAndUpdate(DeferUpdate=False)
    workflow.TaskObject['Generate the Surface Mesh'].Arguments.set_state({r'CFDSurfaceMeshControls': {r'CellsPerGap': 4,r'CurvatureNormalAngle': 9,r'GrowthRate': 1.1,r'MaxSize': 1,r'MinSize': 0.1,},})
    workflow.TaskObject['Generate the Surface Mesh'].Execute()
    workflow.TaskObject['Describe Geometry'].UpdateChildTasks(SetupTypeChanged=False)
    workflow.TaskObject['Generate the Surface Mesh'].InsertNextTask(CommandName=r'ImproveSurfaceMesh')
    workflow.TaskObject['Improve Surface Mesh'].Arguments.set_state({r'FaceQualityLimit': 0.7,r'MeshObject': r'',r'SMImprovePreferences': {r'AdvancedImprove': r'no',r'AllowDefeaturing': r'no',r'SIQualityCollapseLimit': 0.85,r'SIQualityIterations': 5,r'SIQualityMaxAngle': 80,r'SIRemoveStep': r'no',r'SIStepQualityLimit': 0,r'SIStepWidth': 0,r'ShowSMImprovePreferences': False,},r'SQMinSize': 0.1,})
    workflow.TaskObject['Improve Surface Mesh'].Execute()
    workflow.TaskObject['Describe Geometry'].UpdateChildTasks(SetupTypeChanged=False)
    workflow.TaskObject['Describe Geometry'].Arguments.set_state({r'NonConformal': r'No',r'SetupType': r'The geometry consists of only fluid regions with no voids',})
    workflow.TaskObject['Describe Geometry'].UpdateChildTasks(SetupTypeChanged=True)
    workflow.TaskObject['Describe Geometry'].Execute()
    workflow.TaskObject['Update Boundaries'].Arguments.set_state({r'BoundaryLabelList': [r'inlet'],r'BoundaryLabelTypeList': [r'mass-flow-inlet'],r'OldBoundaryLabelList': [r'inlet'],r'OldBoundaryLabelTypeList': [r'velocity-inlet'],})
    workflow.TaskObject['Update Boundaries'].Execute()
    workflow.TaskObject['Update Regions'].Arguments.set_state({r'OldRegionNameList': [r'--'],r'OldRegionTypeList': [r'fluid'],r'RegionNameList': [r'liutizone'],r'RegionTypeList': [r'fluid'],})
    workflow.TaskObject['Update Regions'].Execute()
    workflow.TaskObject['Add Boundary Layers'].Arguments.set_state({r'LocalPrismPreferences': {r'Continuous': r'Continuous',},r'NumberOfLayers': 4,r'Rate': 1.1,})
    workflow.TaskObject['Add Boundary Layers'].AddChildAndUpdate(DeferUpdate=False)
    workflow.TaskObject['Generate the Volume Mesh'].Arguments.set_state({r'VolumeFill': r'polyhedra',r'VolumeFillControls': {r'TetPolyMaxCellLength': 1,},})
    workflow.TaskObject['Generate the Volume Mesh'].Execute()
    workflow.TaskObject['Generate the Volume Mesh'].InsertNextTask(CommandName=r'ImproveVolumeMesh')
    workflow.TaskObject['Improve Volume Mesh'].Arguments.set_state({r'CellQualityLimit': 0.15,r'QualityMethod': r'Orthogonal',r'VMImprovePreferences': {r'ShowVMImprovePreferences': False,r'VIQualityIterations': 5,r'VIQualityMinAngle': 0,r'VIgnoreFeature': r'yes',},})
    workflow.TaskObject['Improve Volume Mesh'].Execute()

    solver = meshing_session.switch_to_solver()
    solver.mesh.check()


    solver.setup.models.energy.enabled = True

    viscous = solver.setup.models.viscous
    viscous.model = "k-epsilon"
    viscous.k_epsilon_model = "rng"

    solver.setup.materials.database.copy_by_name(type="fluid", name="water-liquid")

    zone_name = "liutizone"
    solver.setup.cell_zone_conditions.fluid[zone_name].material = "water-liquid"


    mass_inlet = solver.setup.boundary_conditions.mass_flow_inlet["inlet"]
    mass_inlet.momentum.mass_flow_rate.value = 0.005
    mass_inlet.thermal.total_temperature.value = 293.15

    re_input = solver.setup.boundary_conditions.wall["re"]
    re_input.thermal.q.value = 10000

    solver.solution.methods.p_v_coupling.flow_scheme = "SIMPLE"

    solver.solution.methods.discretization_scheme = {"k" : "second-order-upwind", "epsilon" : "second-order-upwind"}

    resid_eqns = solver.solution.monitor.residual.equations
    resid_eqns["continuity"].absolute_criteria = 1e-6
    resid_eqns["x-velocity"].absolute_criteria = 1e-5
    resid_eqns["y-velocity"].absolute_criteria = 1e-5
    resid_eqns["z-velocity"].absolute_criteria = 1e-5
    resid_eqns["energy"].absolute_criteria = 1e-8
    resid_eqns["k"].absolute_criteria = 1e-5
    resid_eqns["epsilon"].absolute_criteria = 1e-5

    solver.solution.monitor.residual.options.plot = True

    solver.solution.initialization.hybrid_initialize()

    solver.solution.run_calculation.iterate(iter_count=500)

    file_name = os.path.join(output_dir, f"heat_change{number}.cas.h5")

    solver.file.write(
        file_type = "case-data",
        file_name = file_name,
    )

    time.sleep(3)

    solver.exit()
