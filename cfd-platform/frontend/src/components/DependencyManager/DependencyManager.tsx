/**
 * Dependency Manager Component
 * 
 * This component provides a UI for managing CFD platform dependencies.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { 
  Box, 
  VStack, 
  HStack, 
  Text, 
  Button, 
  Card, 
  CardBody, 
  CardHeader,
  Heading,
  Badge,
  Spinner,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  useToast,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  useDisclosure,
  Progress,
  Icon,
  Tooltip,
  Divider,
  SimpleGrid
} from '@chakra-ui/react';
import { 
  FaCheck, 
  FaTimes, 
  FaExclamationTriangle, 
  FaDownload, 
  FaCog, 
  FaSync,
  FaBox,
  FaTools,
  FaCode,
  FaLinux,
  FaDocker,
  FaNodeJs,
  FaPython
} from 'react-icons/fa';
import { SiGmsh, SiFreecad, SiOpenfoam } from 'react-icons/si';

// Types
interface DependencyInfo {
  name: string;
  display_name: string;
  description: string;
  category: string;
  status: string;
  installed_version: string | null;
  required_version: string | null;
  install_path: string | null;
  homepage: string;
  documentation: string;
  dependencies: any[];
}

interface DiagnosticResult {
  healthy: boolean;
  message: string;
  errors: string[];
  warnings: string[];
  severity: string;
  metrics?: Record<string, any>;
}

interface PlatformInfo {
  platform: string;
  architecture: string;
  package_manager: string;
  home_directory: string;
}

// Category icons mapping
const categoryIcons: Record<string, any> = {
  engineering: FaTools,
  platform: FaLinux,
  python_pkg: FaPython
};

// Status colors mapping
const statusColors: Record<string, string> = {
  installed: 'green',
  missing: 'red',
  broken: 'orange',
  outdated: 'yellow'
};

// Status icons mapping
const statusIcons: Record<string, any> = {
  installed: FaCheck,
  missing: FaTimes,
  broken: FaExclamationTriangle,
  outdated: FaDownload
};

export const DependencyManager: React.FC = () => {
  // State
  const [dependencies, setDependencies] = useState<DependencyInfo[]>([]);
  const [platformInfo, setPlatformInfo] = useState<PlatformInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [installing, setInstalling] = useState<Record<string, boolean>>({});
  const [diagnostics, setDiagnostics] = useState<Record<string, DiagnosticResult>>({});
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  
  // Hooks
  const toast = useToast();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedDependency, setSelectedDependency] = useState<DependencyInfo | null>(null);
  
  // API Base URL
  const API_BASE = '/api/v1/dependencies';
  
  // Fetch dependencies
  const fetchDependencies = useCallback(async () => {
    try {
      setLoading(true);
      const url = selectedCategory === 'all' 
        ? API_BASE 
        : `${API_BASE}?category=${selectedCategory}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Failed to fetch dependencies');
      }
      
      const data = await response.json();
      setDependencies(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [selectedCategory]);
  
  // Fetch platform info
  const fetchPlatformInfo = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/platform`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch platform info');
      }
      
      const data = await response.json();
      setPlatformInfo(data);
    } catch (err) {
      console.error('Failed to fetch platform info:', err);
    }
  }, []);
  
  // Run diagnostics for a dependency
  const runDiagnostics = useCallback(async (name: string) => {
    try {
      const response = await fetch(`${API_BASE}/${name}/diagnostics`);
      
      if (!response.ok) {
        throw new Error('Failed to run diagnostics');
      }
      
      const data = await response.json();
      setDiagnostics(prev => ({ ...prev, [name]: data }));
      return data;
    } catch (err) {
      console.error('Failed to run diagnostics:', err);
      return null;
    }
  }, []);
  
  // Install dependency
  const installDependency = useCallback(async (name: string) => {
    try {
      setInstalling(prev => ({ ...prev, [name]: true }));
      
      const response = await fetch(`${API_BASE}/${name}/install`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error('Failed to install dependency');
      }
      
      const data = await response.json();
      
      toast({
        title: 'Installation started',
        description: data.message,
        status: 'info',
        duration: 3000,
        isClosable: true
      });
      
      // Refresh after a delay
      setTimeout(() => {
        fetchDependencies();
        runDiagnostics(name);
      }, 2000);
      
    } catch (err) {
      toast({
        title: 'Installation failed',
        description: err instanceof Error ? err.message : 'Unknown error',
        status: 'error',
        duration: 5000,
        isClosable: true
      });
    } finally {
      setInstalling(prev => ({ ...prev, [name]: false }));
    }
  }, [fetchDependencies, runDiagnostics, toast]);
  
  // Initial fetch
  useEffect(() => {
    fetchDependencies();
    fetchPlatformInfo();
  }, [fetchDependencies, fetchPlatformInfo]);
  
  // Refresh handler
  const handleRefresh = () => {
    fetchDependencies();
    fetchPlatformInfo();
    toast({
      title: 'Refreshing',
      description: 'Dependency information refreshed',
      status: 'info',
      duration: 2000,
      isClosable: true
    });
  };
  
  // Open details modal
  const openDetails = (dep: DependencyInfo) => {
    setSelectedDependency(dep);
    runDiagnostics(dep.name);
    onOpen();
  };
  
  // Filter dependencies by category
  const filteredDependencies = selectedCategory === 'all'
    ? dependencies
    : dependencies.filter(d => d.category === selectedCategory);
  
  // Group dependencies by category
  const groupedDependencies = filteredDependencies.reduce((acc, dep) => {
    const category = dep.category;
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(dep);
    return acc;
  }, {} as Record<string, DependencyInfo[]>);
  
  // Loading state
  if (loading && dependencies.length === 0) {
    return (
      <Box p={8} textAlign="center">
        <Spinner size="xl" color="blue.500" />
        <Text mt={4}>Loading dependencies...</Text>
      </Box>
    );
  }
  
  // Error state
  if (error && dependencies.length === 0) {
    return (
      <Alert status="error">
        <AlertIcon />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }
  
  return (
    <Box p={4}>
      {/* Header */}
      <HStack justify="space-between" mb={6}>
        <Heading size="lg">Dependency Manager</Heading>
        <Button 
          leftIcon={<FaSync />} 
          onClick={handleRefresh}
          isLoading={loading}
        >
          Refresh
        </Button>
      </HStack>
      
      {/* Platform Info */}
      {platformInfo && (
        <Card mb={6}>
          <CardHeader>
            <Heading size="sm">Platform Information</Heading>
          </CardHeader>
          <CardBody>
            <SimpleGrid columns={4} spacing={4}>
              <Box>
                <Text fontSize="sm" color="gray.500">Platform</Text>
                <Text>{platformInfo.platform}</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.500">Architecture</Text>
                <Text>{platformInfo.architecture}</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.500">Package Manager</Text>
                <Text>{platformInfo.package_manager}</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.500">Home Directory</Text>
                <Text noOfLines={1}>{platformInfo.home_directory}</Text>
              </Box>
            </SimpleGrid>
          </CardBody>
        </Card>
      )}
      
      {/* Category Filter */}
      <Tabs 
        variant="soft-rounded" 
        colorScheme="blue" 
        mb={6}
        onChange={(index) => {
          const categories = ['all', 'engineering', 'platform', 'python_pkg'];
          setSelectedCategory(categories[index]);
        }}
      >
        <TabList>
          <Tab>All</Tab>
          <Tab>Engineering Tools</Tab>
          <Tab>Platform</Tab>
          <Tab>Python Packages</Tab>
        </TabList>
      </Tabs>
      
      {/* Dependencies List */}
      <VStack spacing={4} align="stretch">
        {Object.entries(groupedDependencies).map(([category, deps]) => (
          <Card key={category}>
            <CardHeader>
              <HStack>
                <Icon 
                  as={categoryIcons[category] || FaBox} 
                  boxSize={5} 
                />
                <Heading size="md" textTransform="capitalize">
                  {category.replace('_', ' ')}
                </Heading>
                <Badge>{deps.length}</Badge>
              </HStack>
            </CardHeader>
            <CardBody>
              <VStack spacing={3} align="stretch">
                {deps.map((dep) => (
                  <DependencyCard
                    key={dep.name}
                    dependency={dep}
                    diagnostic={diagnostics[dep.name]}
                    onInstall={() => installDependency(dep.name)}
                    onDetails={() => openDetails(dep)}
                    isInstalling={installing[dep.name] || false}
                  />
                ))}
              </VStack>
            </CardBody>
          </Card>
        ))}
      </VStack>
      
      {/* Details Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>{selectedDependency?.display_name}</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {selectedDependency && (
              <DependencyDetails
                dependency={selectedDependency}
                diagnostic={diagnostics[selectedDependency.name]}
              />
            )}
          </ModalBody>
          <ModalFooter>
            <Button onClick={onClose}>Close</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

// Dependency Card Component
interface DependencyCardProps {
  dependency: DependencyInfo;
  diagnostic?: DiagnosticResult;
  onInstall: () => void;
  onDetails: () => void;
  isInstalling: boolean;
}

const DependencyCard: React.FC<DependencyCardProps> = ({
  dependency,
  diagnostic,
  onInstall,
  onDetails,
  isInstalling
}) => {
  const StatusIcon = statusIcons[dependency.status] || FaExclamationTriangle;
  const statusColor = statusColors[dependency.status] || 'gray';
  
  return (
    <Card variant="outline">
      <CardBody>
        <HStack justify="space-between">
          <HStack spacing={4}>
            <Icon as={StatusIcon} color={`${statusColor}.500`} boxSize={5} />
            <Box>
              <Text fontWeight="bold">{dependency.display_name}</Text>
              <Text fontSize="sm" color="gray.500">
                {dependency.description}
              </Text>
            </Box>
          </HStack>
          
          <HStack spacing={4}>
            <VStack spacing={1} align="end">
              <Badge colorScheme={statusColor}>
                {dependency.status}
              </Badge>
              {dependency.installed_version && (
                <Text fontSize="sm" color="gray.500">
                  v{dependency.installed_version}
                </Text>
              )}
            </VStack>
            
            <VStack spacing={2}>
              {dependency.status !== 'installed' && (
                <Button
                  size="sm"
                  colorScheme="blue"
                  leftIcon={<FaDownload />}
                  onClick={onInstall}
                  isLoading={isInstalling}
                >
                  Install
                </Button>
              )}
              <Button
                size="sm"
                variant="ghost"
                onClick={onDetails}
              >
                Details
              </Button>
            </VStack>
          </HStack>
        </HStack>
        
        {/* Diagnostic Warnings */}
        {diagnostic && diagnostic.warnings.length > 0 && (
          <Alert status="warning" mt={3} borderRadius="md">
            <AlertIcon />
            <Text fontSize="sm">{diagnostic.warnings[0]}</Text>
          </Alert>
        )}
      </CardBody>
    </Card>
  );
};

// Dependency Details Component
interface DependencyDetailsProps {
  dependency: DependencyInfo;
  diagnostic?: DiagnosticResult;
}

const DependencyDetails: React.FC<DependencyDetailsProps> = ({
  dependency,
  diagnostic
}) => {
  return (
    <VStack spacing={4} align="stretch">
      {/* Basic Info */}
      <Box>
        <Text fontWeight="bold" mb={2}>Information</Text>
        <SimpleGrid columns={2} spacing={2}>
          <Text color="gray.500">Name:</Text>
          <Text>{dependency.name}</Text>
          <Text color="gray.500">Version:</Text>
          <Text>{dependency.installed_version || 'Not installed'}</Text>
          <Text color="gray.500">Status:</Text>
          <Badge colorScheme={statusColors[dependency.status]}>
            {dependency.status}
          </Badge>
          <Text color="gray.500">Install Path:</Text>
          <Text fontSize="sm" noOfLines={1}>
            {dependency.install_path || 'N/A'}
          </Text>
        </SimpleGrid>
      </Box>
      
      <Divider />
      
      {/* Links */}
      <Box>
        <Text fontWeight="bold" mb={2}>Links</Text>
        <VStack align="start" spacing={1}>
          <Text fontSize="sm">
            <Text as="span" color="gray.500">Homepage: </Text>
            <a href={dependency.homepage} target="_blank" rel="noopener noreferrer">
              {dependency.homepage}
            </a>
          </Text>
          <Text fontSize="sm">
            <Text as="span" color="gray.500">Documentation: </Text>
            <a href={dependency.documentation} target="_blank" rel="noopener noreferrer">
              {dependency.documentation}
            </a>
          </Text>
        </VStack>
      </Box>
      
      <Divider />
      
      {/* Diagnostic Results */}
      {diagnostic && (
        <Box>
          <Text fontWeight="bold" mb={2}>Diagnostics</Text>
          <Alert 
            status={diagnostic.healthy ? 'success' : 'error'} 
            borderRadius="md"
            mb={2}
          >
            <AlertIcon />
            <Text>{diagnostic.message}</Text>
          </Alert>
          
          {diagnostic.errors.length > 0 && (
            <Box mb={2}>
              <Text fontSize="sm" fontWeight="bold" color="red.500">Errors:</Text>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {diagnostic.errors.map((err, i) => (
                  <li key={i}>
                    <Text fontSize="sm" color="red.500">{err}</Text>
                  </li>
                ))}
              </ul>
            </Box>
          )}
          
          {diagnostic.warnings.length > 0 && (
            <Box mb={2}>
              <Text fontSize="sm" fontWeight="bold" color="orange.500">Warnings:</Text>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {diagnostic.warnings.map((warn, i) => (
                  <li key={i}>
                    <Text fontSize="sm" color="orange.500">{warn}</Text>
                  </li>
                ))}
              </ul>
            </Box>
          )}
          
          {diagnostic.metrics && Object.keys(diagnostic.metrics).length > 0 && (
            <Box>
              <Text fontSize="sm" fontWeight="bold" mb={1}>Metrics:</Text>
              <SimpleGrid columns={2} spacing={1}>
                {Object.entries(diagnostic.metrics).map(([key, value]) => (
                  <React.Fragment key={key}>
                    <Text fontSize="sm" color="gray.500">{key}:</Text>
                    <Text fontSize="sm">{JSON.stringify(value)}</Text>
                  </React.Fragment>
                ))}
              </SimpleGrid>
            </Box>
          )}
        </Box>
      )}
    </VStack>
  );
};

export default DependencyManager;