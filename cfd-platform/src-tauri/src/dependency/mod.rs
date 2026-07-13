//! Dependency management module for HX CFD
//! 
//! Manages the 14 dependencies: 11 install-time (ZIP archives) and 3 build-time (npm packages).

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use crate::config::AppConfig;
use crate::error::{HxCfdError, HxCfdResult};

/// Component status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ComponentStatus {
    /// Component is not installed
    NotInstalled,
    /// Component is currently being installed
    Installing,
    /// Component is installed
    Installed,
    /// Installation failed
    Failed(String),
}

/// A dependency component
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Component {
    /// Component identifier
    pub id: String,
    /// Display name
    pub name: String,
    /// Version string
    pub version: String,
    /// Path to the component
    pub path: PathBuf,
    /// Installation status
    pub status: ComponentStatus,
    /// Whether this is an optional component
    pub optional: bool,
    /// Size in bytes
    pub size: u64,
    /// SHA256 checksum
    pub checksum: String,
}

impl Component {
    /// Check if the component is installed
    pub fn is_installed(&self) -> bool {
        self.status == ComponentStatus::Installed && self.path.exists()
    }
    
    /// Get the executable path for this component
    pub fn get_executable(&self, name: &str) -> Option<PathBuf> {
        let exe_path = self.path.join("bin").join(name);
        if exe_path.exists() {
            Some(exe_path)
        } else {
            None
        }
    }
}

/// Dependency manager
#[derive(Debug, Clone)]
pub struct DependencyManager {
    /// List of all components
    pub components: Vec<Component>,
    /// Dependencies directory
    pub dependencies_dir: PathBuf,
}

impl DependencyManager {
    /// Create a new dependency manager
    pub fn new(config: &AppConfig) -> Self {
        let dependencies_dir = config.dependencies_dir.clone();
        
        // Define all 14 components
        let components = vec![
            // 11 install-time components
            Component {
                id: "hx-cfd-runtime".to_string(),
                name: "HX CFD Runtime".to_string(),
                version: "1.0.0".to_string(),
                path: dependencies_dir.join("hx-cfd-runtime"),
                status: ComponentStatus::NotInstalled,
                optional: false,
                size: 50_000_000,
                checksum: String::new(),
            },
            Component {
                id: "hx-cfd-python".to_string(),
                name: "Python Runtime".to_string(),
                version: "3.11".to_string(),
                path: dependencies_dir.join("python"),
                status: ComponentStatus::NotInstalled,
                optional: false,
                size: 30_000_000,
                checksum: String::new(),
            },
            Component {
                id: "openfoam-runtime".to_string(),
                name: "OpenFOAM".to_string(),
                version: "v10".to_string(),
                path: dependencies_dir.join("openfoam"),
                status: ComponentStatus::NotInstalled,
                optional: false,
                size: 500_000_000,
                checksum: String::new(),
            },
            Component {
                id: "gmsh-runtime".to_string(),
                name: "Gmsh".to_string(),
                version: "4.12".to_string(),
                path: dependencies_dir.join("gmsh"),
                status: ComponentStatus::NotInstalled,
                optional: false,
                size: 100_000_000,
                checksum: String::new(),
            },
            Component {
                id: "paraview-runtime".to_string(),
                name: "ParaView".to_string(),
                version: "5.12".to_string(),
                path: dependencies_dir.join("paraview"),
                status: ComponentStatus::NotInstalled,
                optional: false,
                size: 400_000_000,
                checksum: String::new(),
            },
            Component {
                id: "freecad-runtime".to_string(),
                name: "FreeCAD".to_string(),
                version: "0.21".to_string(),
                path: dependencies_dir.join("freecad"),
                status: ComponentStatus::NotInstalled,
                optional: false,
                size: 500_000_000,
                checksum: String::new(),
            },
            Component {
                id: "meshio-package".to_string(),
                name: "meshio".to_string(),
                version: "5.3".to_string(),
                path: dependencies_dir.join("python/lib/site-packages/meshio"),
                status: ComponentStatus::NotInstalled,
                optional: false,
                size: 5_000_000,
                checksum: String::new(),
            },
            Component {
                id: "openmdao-package".to_string(),
                name: "OpenMDAO".to_string(),
                version: "3.26".to_string(),
                path: dependencies_dir.join("python/lib/site-packages/openmdao"),
                status: ComponentStatus::NotInstalled,
                optional: false,
                size: 20_000_000,
                checksum: String::new(),
            },
            Component {
                id: "nevergrad-package".to_string(),
                name: "nevergrad".to_string(),
                version: "0.7".to_string(),
                path: dependencies_dir.join("python/lib/site-packages/nevergrad"),
                status: ComponentStatus::NotInstalled,
                optional: false,
                size: 10_000_000,
                checksum: String::new(),
            },
            Component {
                id: "pyvista-package".to_string(),
                name: "PyVista".to_string(),
                version: "0.42".to_string(),
                path: dependencies_dir.join("python/lib/site-packages/pyvista"),
                status: ComponentStatus::NotInstalled,
                optional: false,
                size: 50_000_000,
                checksum: String::new(),
            },
            Component {
                id: "vtk-package".to_string(),
                name: "VTK".to_string(),
                version: "9.3".to_string(),
                path: dependencies_dir.join("python/lib/site-packages/vtk"),
                status: ComponentStatus::NotInstalled,
                optional: false,
                size: 100_000_000,
                checksum: String::new(),
            },
            // 2 optional components
            Component {
                id: "hx-cfd-examples".to_string(),
                name: "Example Cases".to_string(),
                version: "1.0.0".to_string(),
                path: dependencies_dir.join("examples"),
                status: ComponentStatus::NotInstalled,
                optional: true,
                size: 200_000_000,
                checksum: String::new(),
            },
            Component {
                id: "hx-cfd-docs".to_string(),
                name: "Documentation".to_string(),
                version: "1.0.0".to_string(),
                path: dependencies_dir.join("docs"),
                status: ComponentStatus::NotInstalled,
                optional: true,
                size: 50_000_000,
                checksum: String::new(),
            },
        ];
        
        Self {
            components,
            dependencies_dir,
        }
    }
    
    /// Get a component by ID
    pub fn get_component(&self, id: &str) -> Option<&Component> {
        self.components.iter().find(|c| c.id == id)
    }
    
    /// Get a mutable component by ID
    pub fn get_component_mut(&mut self, id: &str) -> Option<&mut Component> {
        self.components.iter_mut().find(|c| c.id == id)
    }
    
    /// Get all required (non-optional) components
    pub fn required_components(&self) -> Vec<&Component> {
        self.components.iter().filter(|c| !c.optional).collect()
    }
    
    /// Get all optional components
    pub fn optional_components(&self) -> Vec<&Component> {
        self.components.iter().filter(|c| c.optional).collect()
    }
    
    /// Check if all required components are installed
    pub fn all_required_installed(&self) -> bool {
        self.required_components().iter().all(|c| c.is_installed())
    }
    
    /// Get the count of installed components
    pub fn installed_count(&self) -> usize {
        self.components.iter().filter(|c| c.is_installed()).count()
    }
    
    /// Get the total count of components
    pub fn total_count(&self) -> usize {
        self.components.len()
    }
    
    /// Get installation progress (0.0 to 1.0)
    pub fn installation_progress(&self) -> f64 {
        let installed = self.installed_count() as f64;
        let total = self.total_count() as f64;
        if total > 0.0 {
            installed / total
        } else {
            0.0
        }
    }
}