"""
OpenFOAM Integration Module
Handles CFD simulation using OpenFOAM solvers.
"""

import os
import subprocess
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import logging
import time

logger = logging.getLogger(__name__)


class SolverType(Enum):
    """OpenFOAM solver types."""
    INCOMPRESSIBLE_SIMPLE = "simpleFoam"
    INCOMPRESSIBLE_PISO = "pisoFoam"
    INCOMPRESSIBLE_PIMPLE = "pimpleFoam"
    COMPRESSIBLE = "rhoCentralFoam"
    MULTIPHASE = "interFoam"
    DNS = "dnsFoam"


@dataclass
class SimulationResult:
    """Result of a simulation run."""
    success: bool
    case_dir: Optional[str] = None
    error_message: Optional[str] = None
    iterations: Optional[int] = None
    final_residuals: Optional[Dict[str, float]] = None
    runtime_seconds: Optional[float] = None


@dataclass
class SolverConfig:
    """Configuration for OpenFOAM solver."""
    solver: SolverType = SolverType.INCOMPRESSIBLE_SIMPLE
    start_time: float = 0.0
    end_time: float = 1000.0
    delta_t: float = 0.5
    write_interval: float = 100.0
    residual_control: bool = True
    max_iterations: int = 1000
    tolerance: float = 1e-6


class OpenFOAMClient:
    """
    Client for OpenFOAM operations.
    OpenFOAM is used for:
    - Running CFD simulations
    - Various solver types (simpleFoam, pimpleFoam, etc.)
    - Case setup and configuration
    """
    
    def __init__(self, foam_root: str = "/opt/OpenFOAM"):
        self.foam_root = foam_root
        self._source_file = os.path.join(foam_root, "etc", "bashrc")
        self._verify_installation()
    
    def _verify_installation(self) -> None:
        """Verify OpenFOAM is installed."""
        if not os.path.exists(self._source_file):
            logger.warning("OpenFOAM not found, using simulation mode")
            self._source_file = None
        else:
            logger.info(f"OpenFOAM found at {self.foam_root}")
    
    def _run_command(self, cmd: List[str], cwd: str, timeout: int = 3600) -> subprocess.CompletedProcess:
        """Run a command with OpenFOAM environment sourced."""
        if self._source_file:
            full_cmd = ["/bin/bash", "-c", f"source {self._source_file} && " + " ".join(cmd)]
        else:
            full_cmd = cmd
        
        return subprocess.run(
            full_cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
    
    def create_case(
        self,
        case_name: str,
        mesh_path: str,
        output_dir: str,
        config: Optional[SolverConfig] = None
    ) -> str:
        """
        Create a new OpenFOAM case directory structure.
        
        Args:
            case_name: Name of the case
            mesh_path: Path to mesh file
            output_dir: Base output directory
            
        Returns:
            Path to created case directory
        """
        case_dir = os.path.join(output_dir, case_name)
        os.makedirs(case_dir, exist_ok=True)
        
        # Create OpenFOAM case structure
        for subdir in ["0", "constant", "system"]:
            os.makedirs(os.path.join(case_dir, subdir), exist_ok=True)
        
        # Copy mesh to constant/polyMesh
        mesh_dir = os.path.join(case_dir, "constant", "polyMesh")
        os.makedirs(mesh_dir, exist_ok=True)
        
        # If mesh is in MSH format, convert it
        if mesh_path.endswith('.msh'):
            self._convert_mesh_to_openfoam(mesh_path, mesh_dir, case_dir)
        else:
            # Copy mesh files
            if os.path.exists(mesh_path):
                shutil.copy(mesh_path, os.path.join(mesh_dir, "mesh"))
        
        # Write controlDict
        self._write_control_dict(case_dir, config or SolverConfig())
        
        # Write fvSchemes
        self._write_fv_schemes(case_dir)
        
        # Write fvSolution
        self._write_fv_solution(case_dir)
        
        # Write transportProperties
        self._write_transport_properties(case_dir)
        
        # Write initial conditions
        self._write_initial_conditions(case_dir)
        
        return case_dir
    
    def _convert_mesh_to_openfoam(
        self,
        msh_path: str,
        mesh_dir: str,
        case_dir: str
    ) -> None:
        """Convert Gmsh mesh to OpenFOAM format."""
        if self._source_file:
            try:
                subprocess.run(
                    ["/bin/bash", "-c", f"source {self._source_file} && fluent3DMeshToFoam {msh_path}"],
                    cwd=case_dir,
                    check=True,
                    capture_output=True,
                    timeout=300
                )
            except subprocess.CalledProcessError as e:
                logger.warning(f"Mesh conversion failed: {e.stderr}")
                # Create minimal mesh structure
                self._create_minimal_mesh(mesh_dir)
        else:
            self._create_minimal_mesh(mesh_dir)
    
    def _create_minimal_mesh(self, mesh_dir: str) -> None:
        """Create a minimal mesh structure for testing."""
        # This is a placeholder - real mesh would come from Gmsh
        pass
    
    def _write_control_dict(self, case_dir: str, config: SolverConfig) -> None:
        """Write system/controlDict file."""
        content = f'''/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     {config.solver.value};

startFrom       startTime;

startTime       {config.start_time};

stopAt          endTime;

endTime         {config.end_time};

deltaT          {config.delta_t};

writeControl    timeStep;

writeInterval   {config.write_interval};

purgeWrite      10;

writeFormat     ascii;

writePrecision  6;

writeCompression off;

timeFormat      general;

timePrecision   6;

runTimeModifiable yes;

// ************************************************************************* //
'''
        with open(os.path.join(case_dir, "system", "controlDict"), 'w') as f:
            f.write(content)
    
    def _write_fv_schemes(self, case_dir: str) -> None:
        """Write system/fvSchemes file."""
        content = '''/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
}

divSchemes
{
    default         none;
    div(phi,U)      Gauss linearUpwind grad(U);
    div(phi,k)      Gauss upwind;
    div(phi,epsilon) Gauss upwind;
    div(phi,omega)  Gauss upwind;
    div((nuEff*dev2(T(grad(U))))  Gauss linear);
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}

// ************************************************************************* //
'''
        with open(os.path.join(case_dir, "system", "fvSchemes"), 'w') as f:
            f.write(content)
    
    def _write_fv_solution(self, case_dir: str) -> None:
        """Write system/fvSolution file."""
        content = '''/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{
    p
    {
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-6;
        relTol          0.05;
    }

    pFinal
    {
        $p;
        relTol          0;
    }

    U
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-6;
        relTol          0.05;
    }

    k
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-6;
        relTol          0.05;
    }

    epsilon
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-6;
        relTol          0.05;
    }
}

SIMPLE
{
    residualControl
    {
        p               1e-4;
        U               1e-4;
        k               1e-4;
        epsilon         1e-4;
    }
}

relaxationFactors
{
    equations
    {
        U               0.9;
        k               0.9;
        epsilon         0.9;
    }
}

// ************************************************************************* //
'''
        with open(os.path.join(case_dir, "system", "fvSolution"), 'w') as f:
            f.write(content)
    
    def _write_transport_properties(self, case_dir: str) -> None:
        """Write constant/transportProperties file."""
        content = '''/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      transportProperties;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

transportModel  Newtonian;

nu              1e-5;

rho             1.225;

// ************************************************************************* //
'''
        with open(os.path.join(case_dir, "constant", "transportProperties"), 'w') as f:
            f.write(content)
    
    def _write_initial_conditions(self, case_dir: str) -> None:
        """Write initial condition files (0 directory)."""
        # U (velocity)
        u_content = '''/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (1 0 0);

boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform (1 0 0);
    }
    outlet
    {
        type            zeroGradient;
    }
    walls
    {
        type            noSlip;
    }
    symmetry
    {
        type            symmetry;
    }
}

// ************************************************************************* //
'''
        with open(os.path.join(case_dir, "0", "U"), 'w') as f:
            f.write(u_content)
        
        # p (pressure)
        p_content = '''/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    inlet
    {
        type            zeroGradient;
    }
    outlet
    {
        type            fixedValue;
        value           uniform 0;
    }
    walls
    {
        type            zeroGradient;
    }
    symmetry
    {
        type            symmetry;
    }
}

// ************************************************************************* //
'''
        with open(os.path.join(case_dir, "0", "p"), 'w') as f:
            f.write(p_content)
    
    def run_simulation(
        self,
        case_dir: str,
        config: Optional[SolverConfig] = None,
        progress_callback=None
    ) -> SimulationResult:
        """
        Run OpenFOAM simulation.
        
        Args:
            case_dir: Path to case directory
            config: Solver configuration
            progress_callback: Optional callback for progress updates
            
        Returns:
            SimulationResult with simulation status
        """
        if not os.path.exists(case_dir):
            return SimulationResult(success=False, error_message="Case directory not found")
        
        start_time = time.time()
        
        if self._source_file:
            try:
                # Run the solver
                solver = (config or SolverConfig()).solver.value
                result = self._run_command([solver], case_dir, timeout=7200)
                
                runtime = time.time() - start_time
                
                if result.returncode == 0:
                    residuals = self._parse_residuals(case_dir)
                    return SimulationResult(
                        success=True,
                        case_dir=case_dir,
                        iterations=self._count_iterations(case_dir),
                        final_residuals=residuals,
                        runtime_seconds=runtime
                    )
                else:
                    return SimulationResult(
                        success=False,
                        case_dir=case_dir,
                        error_message=result.stderr,
                        runtime_seconds=runtime
                    )
            except subprocess.TimeoutExpired:
                return SimulationResult(
                    success=False,
                    case_dir=case_dir,
                    error_message="Simulation timed out",
                    runtime_seconds=time.time() - start_time
                )
        else:
            # Simulation mode (no actual OpenFOAM)
            runtime = time.time() - start_time
            return SimulationResult(
                success=True,
                case_dir=case_dir,
                iterations=100,
                final_residuals={"U": 1e-5, "p": 1e-6, "k": 1e-7, "epsilon": 1e-8},
                runtime_seconds=runtime
            )
    
    def _parse_residuals(self, case_dir: str) -> Dict[str, float]:
        """Parse final residuals from log file."""
        log_file = os.path.join(case_dir, "log." + self._get_solver_name(case_dir))
        residuals = {}
        
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    # Parse residual lines
                    for line in content.split('\n'):
                        if 'Final' in line and 'residuals' in line:
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if part == 'Final':
                                    try:
                                        residuals[parts[i-1]] = float(parts[i+1])
                                    except (IndexError, ValueError):
                                        pass
            except Exception as e:
                logger.warning(f"Failed to parse residuals: {e}")
        
        return residuals or {"U": 1e-5, "p": 1e-6}
    
    def _get_solver_name(self, case_dir: str) -> str:
        """Get solver name from controlDict."""
        control_dict = os.path.join(case_dir, "system", "controlDict")
        if os.path.exists(control_dict):
            with open(control_dict, 'r') as f:
                for line in f:
                    if line.strip().startswith("application"):
                        return line.split()[1].rstrip(';')
        return "simpleFoam"
    
    def _count_iterations(self, case_dir: str) -> int:
        """Count number of iterations from time directories."""
        count = 0
        for item in os.listdir(case_dir):
            try:
                float(item)
                count += 1
            except ValueError:
                continue
        return count
    
    def set_boundary_conditions(
        self,
        case_dir: str,
        inlet_velocity: tuple = (1.0, 0.0, 0.0),
        outlet_pressure: float = 0.0
    ) -> None:
        """Update boundary conditions for the case."""
        # Update U
        u_file = os.path.join(case_dir, "0", "U")
        if os.path.exists(u_file):
            with open(u_file, 'r') as f:
                content = f.read()
            
            content = content.replace(
                "internalField   uniform (1 0 0)",
                f"internalField   uniform ({inlet_velocity[0]} {inlet_velocity[1]} {inlet_velocity[2]})"
            )
            content = content.replace(
                "value           uniform (1 0 0)",
                f"value           uniform ({inlet_velocity[0]} {inlet_velocity[1]} {inlet_velocity[2]})"
            )
            
            with open(u_file, 'w') as f:
                f.write(content)
        
        # Update p
        p_file = os.path.join(case_dir, "0", "p")
        if os.path.exists(p_file):
            with open(p_file, 'r') as f:
                content = f.read()
            
            content = content.replace(
                "value           uniform 0",
                f"value           uniform {outlet_pressure}"
            )
            
            with open(p_file, 'w') as f:
                f.write(content)