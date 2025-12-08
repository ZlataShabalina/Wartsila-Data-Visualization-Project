import { useCallback, useState, useEffect, type ChangeEvent } from 'react';
import {
  ReactFlow,
  applyNodeChanges,
  applyEdgeChanges,
  type NodeChange,
  type Node,
  type Edge,
  type EdgeChange,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  useReactFlow
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import Offcanvas from 'react-bootstrap/Offcanvas';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import ButtonGroup from 'react-bootstrap/ButtonGroup';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type { childNodeResponse, DatasetInfo, DatasetsByConnection, sourcesResponse } from '../responseTypes';
import { TreeLayout } from '../core/TreeLayout';
import CustomNode from './CustomNode';
import { Maximize2, Minimize2, Sun, Moon, Database, Search, FileText, Clock, ZoomIn, ZoomOut, Maximize } from 'lucide-react';
import { nodeService, sourceService } from '../services/service-instances';
import { Modal } from 'react-bootstrap';

type formattedSource = {
  connectionId: number,
  datasetId: number,
  originalName: string,
  size: number,
  modifiedAt: number
}

let treeLayout: TreeLayout;

const nodeTypes = {
  customNode: CustomNode
};

export default function Graph() {
  const navigate = useNavigate();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [show, setShow] = useState(false);
  const [filesUsed, setFilesUsed] = useState<formattedSource[]>([]);
  const [searchString, setSearchString] = useState<string>('');
  const [showConfirm, setShowConfirm] = useState(false);
  const [selectedSource, setSelectedSource] = useState<formattedSource>();
  const [numberChildren, setNumberChildren] = useState<number | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [layout, setLayout] = useState<'vertical' | 'horizontal'>('horizontal');
  const [searchParams] = useSearchParams();
  const datasetId = parseInt(searchParams.get("datasetId")!);

  const handleClose = () => setShow(false);
  const handleShow = () => setShow(true);
  const handleCloseConfirmation = () => {
    setSelectedSource(undefined);
    setShowConfirm(false);
  }
  const handleShowConfirmation = (source: formattedSource) => {
    setSelectedSource(source);
    setShowConfirm(true);
  }

  useEffect(() => {
    sourceService.getSources().then(res => {
      if (res) {
        setFilesUsed(formatSources(res, datasetId));
      }
    });
    nodeService.getRootNode(datasetId).then(res => {
      const rootNodeId = res?.root_nodes[0];
      const numberChildrenCount = rootNodeId ? res?.children_count[rootNodeId] : 0;
      console.log(res?.children_count.rootNodeId)
      treeLayout = new TreeLayout(
        {
          id: rootNodeId,
          name: rootNodeId,
          children: [],
          numChildren: numberChildrenCount
        },
        [120, 40],
        50,
      'horizontal'
      );
      const [initNodes, initEdges] = treeLayout.getTreeLayout();
      setNodes(initNodes);
      setEdges(initEdges);
    });
  }, [datasetId]);

 
  useEffect(() => {
    if (treeLayout) {
      treeLayout.setLayout(layout);
      const [newNodes, newEdges] = treeLayout.getTreeLayout();
      setNodes(newNodes);
      setEdges(newEdges);
    }
  }, [layout]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes(nodesSnapshot => applyNodeChanges(changes, nodesSnapshot)),
    []
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange<Edge>[]) => setEdges(edgesSnapshot => applyEdgeChanges(changes, edgesSnapshot)),
    []
  );
  const onNodeClick = async (_event: React.MouseEvent, node: Node) => {
    const childrenExpanded = treeLayout.numberOfChildren(node.id)
    const childrenToFetch = numberChildren ? (numberChildren + childrenExpanded) : null;
    const children: childNodeResponse | null = await nodeService.getChildNodes(datasetId, node.id, childrenToFetch);
    if (!children) return;
    const fullyExpanded = children.count_children === childrenExpanded;
    if (!fullyExpanded) {
      const childrenNodes = children.children.map(child => {
        return {
          id: child.id,
          name: child.name,
          children: [],
          numChildren: child.num_children ?? 0
        };
      });
      treeLayout.expandNode(node.id, childrenNodes);
      const [newNodes, newEdges] = treeLayout.getTreeLayout();
      setNodes(newNodes);
      setEdges(newEdges);
    } else {
      treeLayout.collapseNode(node.id);
      const [newNodes, newEdges] = treeLayout.getTreeLayout();
      setNodes(newNodes);
      setEdges(newEdges);
    }
  };

  const handleNewSource = async () => {
    if (!selectedSource) {
      console.error("Hmmm, no new source has been selected");
      return;
    }
    navigate(`/graph?datasetId=${selectedSource.datasetId}`);
    handleCloseConfirmation();
    handleClose();
  }

  const handleSearch = async (nodeId: string) => {
    const pathResp = await nodeService.getNodePath(datasetId, nodeId);
    if (!pathResp) return;

    treeLayout.expandPath(pathResp.path.path);
    const [newNodes, newEdges] = treeLayout.getTreeLayout();
    setNodes(newNodes);
    setEdges(newEdges);
    handleClose();
  };

  function handleOnChange(event: ChangeEvent<HTMLInputElement>): void {
    setSearchString(event.target.value);
  }
  
  const handleNumChildrenChange = (event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value == '0' || event.target.value == '' ? null : parseInt(event.target.value)
    setNumberChildren(value);
  }

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const containerStyle: React.CSSProperties = {
    background: theme === 'light' 
      ? 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)'
      : 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
    minHeight: '100vh',
    transition: 'background 0.3s ease'
  };

  const optionsSectionStyle: React.CSSProperties = {
    background: theme === 'light'
      ? 'rgba(255, 255, 255, 0.95)'
      : 'rgba(45, 45, 45, 0.95)',
    backdropFilter: 'blur(10px)',
    border: theme === 'light' ? '1px solid rgba(255, 255, 255, 0.5)' : '1px solid rgba(68, 68, 68, 0.5)',
    borderRadius: '16px',
    padding: '24px',
    marginBottom: '24px',
    boxShadow: theme === 'light'
      ? '0 8px 32px 0 rgba(31, 38, 135, 0.15)'
      : '0 8px 32px 0 rgba(0, 0, 0, 0.4)',
    transition: 'all 0.3s ease'
  };

  const graphSectionStyle: React.CSSProperties = {
    background: theme === 'light'
      ? 'rgba(255, 255, 255, 0.95)'
      : 'rgba(45, 45, 45, 0.95)',
    backdropFilter: 'blur(10px)',
    border: theme === 'light' ? '1px solid rgba(255, 255, 255, 0.5)' : '1px solid rgba(68, 68, 68, 0.5)',
    borderRadius: '16px',
    boxShadow: theme === 'light'
      ? '0 8px 32px 0 rgba(31, 38, 135, 0.15)'
      : '0 8px 32px 0 rgba(0, 0, 0, 0.4)',
    overflow: 'hidden',
    transition: 'all 0.3s ease'
  };

  const textStyle: React.CSSProperties = {
    color: theme === 'light' ? '#2d3748' : '#e2e8f0'
  };

  const sidebarStyle: React.CSSProperties = {
    background: theme === 'light'
      ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
      : 'linear-gradient(135deg, #434343 0%, #000000 100%)',
    color: 'white'
  };

  const getButtonVariant = (targetLayout: 'vertical' | 'horizontal') => {
    if (layout === targetLayout) {
      return theme === 'light' ? 'primary' : 'light';
    }
    return theme === 'light' ? 'outline-secondary' : 'outline-light';
  };

  return (
    <div style={containerStyle}>
       <Modal show={showConfirm} onHide={handleCloseConfirmation}>
        <Modal.Header closeButton>
          <Modal.Title>Switch sources</Modal.Title>
        </Modal.Header>
        <Modal.Body>Are you sure you would like to switch sources</Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleCloseConfirmation}>
            Keep this source
          </Button>
          <Button variant="primary" onClick={handleNewSource}>
            Change to new source
          </Button>
        </Modal.Footer>
      </Modal>
      <Offcanvas 
        show={show} 
        onHide={handleClose}
        style={{ 
          width: '450px',
          ...sidebarStyle
        }}
      >
        <Offcanvas.Header closeButton style={{ borderBottom: '1px solid rgba(255,255,255,0.2)', paddingBottom: '20px' }}>
          <Offcanvas.Title style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '1.5rem', fontWeight: 700 }}>
            <Database size={28} />
            Manage Data
          </Offcanvas.Title>
        </Offcanvas.Header>
        <Offcanvas.Body style={{ padding: '24px' }}>
          <div style={{ 
            background: 'rgba(255, 255, 255, 0.15)', 
            backdropFilter: 'blur(10px)',
            borderRadius: '12px', 
            padding: '20px',
            marginBottom: '24px',
            border: '1px solid rgba(255, 255, 255, 0.2)'
          }}>
            <Form.Label>
              Number of Children to Expand:
            </Form.Label>
            <br/>
            <input 
              type="number"
              value={numberChildren ?? 0}
              onChange={handleNumChildrenChange}
              min={0}
              max={100}
              step={1}
            />
            <p>{numberChildren ? '' : '**All Nodes will be fetched'}</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <Search size={20} />
              <span style={{ fontWeight: 600, fontSize: '1.1rem' }}>Search Graph</span>
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <Form.Control 
                type="text" 
                placeholder="Enter search query..." 
                value={searchString}
                onChange={handleOnChange}
                style={{
                  background: 'rgba(255, 255, 255, 0.9)',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '10px 14px'
                }}
              />
              <Button 
                variant="light" 
                onClick={() => handleSearch(searchString)}
                style={{
                  borderRadius: '8px',
                  padding: '10px 20px',
                  fontWeight: 600,
                  whiteSpace: 'nowrap'
                }}
              >
                Search
              </Button>
            </div>
          </div>
          <div style={{
            background: 'rgba(255, 255, 255, 0.15)',
            backdropFilter: 'blur(10px)',
            borderRadius: '12px',
            padding: '20px',
            border: '1px solid rgba(255, 255, 255, 0.2)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <FileText size={20} />
              <span style={{ fontWeight: 600, fontSize: '1.1rem' }}>Recent Files</span>
            </div>
            
            {filesUsed.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {filesUsed.map((f, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: 'rgba(255, 255, 255, 0.9)',
                      borderRadius: '8px',
                      padding: '14px 16px',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      border: '1px solid transparent'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(255, 255, 255, 1)';
                      e.currentTarget.style.transform = 'translateX(4px)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'rgba(255, 255, 255, 0.9)';
                      e.currentTarget.style.transform = 'translateX(0)';
                    }}
                    onClick={() => handleShowConfirmation(f)}
                  >
                    <div style={{ fontWeight: 600, color: '#2d3748', marginBottom: '4px' }}>
                      {f.originalName}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.85rem', color: '#718096' }}>
                      <span>{formatFileSize(f.size)}</span>
                      <span>•</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={14} />
                        {formatDate(f.modifiedAt)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ 
                textAlign: 'center', 
                padding: '20px',
                color: 'rgba(255, 255, 255, 0.7)',
                fontSize: '0.95rem'
              }}>
                No recent files
              </div>
            )}
          </div>
        </Offcanvas.Body>
      </Offcanvas>
      {!isFullscreen && (
        <div style={{ padding: '40px', maxWidth: '1600px', margin: '0 auto' }}>
          <div style={{ marginBottom: '32px', textAlign: 'center' }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              background: theme === 'light'
                ? 'linear-gradient(135deg, #fea35dff 0%, #ff6f00ff 100%)'
                : 'linear-gradient(135deg, #434343 0%, #000000 100%)',
              marginBottom: '16px',
              boxShadow: theme === 'light'
                ? '0 4px 20px rgba(102, 126, 234, 0.4)'
                : '0 4px 20px rgba(0, 0, 0, 0.6)'
            }}>
              <Database size={32} color="white" />
            </div>
            <h2 style={{
              ...textStyle,
              fontWeight: 700,
              fontSize: '2rem',
              marginBottom: '8px'
            }}>
              Data Visualization
            </h2>
            <p style={{
              ...textStyle,
              opacity: 0.7,
              fontSize: '1.05rem'
            }}>
              Explore your data through an interactive node graph
            </p>
          </div>


          <div style={optionsSectionStyle}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center', 
              flexWrap: 'wrap', 
              gap: '20px' 
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap' }}>
                <Button
                  onClick={handleShow}
                  style={{
                    background: theme === 'light'
                      ? 'linear-gradient(100deg, #6784f6ff 0%, #0022ffff 100%)'
                      : 'linear-gradient(135deg, #434343 0%, #000000 100%)',
                    border: 'none',
                    borderRadius: '10px',
                    padding: '10px 20px',
                    color: 'white',
                    fontWeight: 600,
                    boxShadow: theme === 'light'
                      ? '0 4px 15px rgba(102, 126, 234, 0.3)'
                      : '0 4px 15px rgba(0, 0, 0, 0.4)',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = theme === 'light'
                      ? '0 6px 20px rgba(102, 126, 234, 0.4)'
                      : '0 6px 20px rgba(0, 0, 0, 0.5)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = theme === 'light'
                      ? '0 4px 15px rgba(102, 126, 234, 0.3)'
                      : '0 4px 15px rgba(0, 0, 0, 0.4)';
                  }}
                >
                  <Database size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
                  Manage Data
                </Button>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ ...textStyle, fontWeight: 500, fontSize: '0.95rem' }}>Layout:</span>
                  <ButtonGroup size="sm">
                    <Button
                      variant={getButtonVariant('horizontal')}
                      onClick={() => setLayout('horizontal')}
                      style={{ 
                        borderRadius: '8px 0 0 8px',
                        fontWeight: 500,
                        padding: '8px 16px'
                      }}
                    >
                      Vertical
                    </Button>
                    <Button
                      variant={getButtonVariant('vertical')}
                      onClick={() => setLayout('vertical')}
                      style={{ 
                        borderRadius: '0 8px 8px 0',
                        fontWeight: 500,
                        padding: '8px 16px'
                      }}
                    >
                      Horizontal
                    </Button>
                  </ButtonGroup>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ ...textStyle, fontWeight: 500, fontSize: '0.95rem' }}>Theme:</span>
                  <Button
                    variant={theme === 'light' ? 'outline-secondary' : 'outline-light'}
                    size="sm"
                    onClick={toggleTheme}
                    style={{
                      borderRadius: '8px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontWeight: 500,
                      padding: '8px 16px'
                    }}
                  >
                    {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
                    {theme === 'light' ? 'Dark' : 'Light'}
                  </Button>
                </div>
              </div>
              <Button
                variant={theme === 'light' ? 'outline-secondary' : 'outline-light'}
                size="sm"
                onClick={toggleFullscreen}
                style={{
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontWeight: 500,
                  padding: '8px 16px'
                }}
              >
                <Maximize2 size={16} />
                Fullscreen
              </Button>
            </div>
          </div>

          <div style={{ ...graphSectionStyle, height: '650px' }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              fitView
              minZoom={0.1}
              maxZoom={4}
              defaultViewport={{ x: 0, y: 0, zoom: 1 }}
            >
              <Background 
                variant={BackgroundVariant.Dots} 
                gap={16} 
                size={1}
                color={theme === 'light' ? '#ddd' : '#444'}
              />
              <Controls 
                style={{
                  background: theme === 'light' ? 'rgba(255, 255, 255, 0.9)' : 'rgba(45, 45, 45, 0.9)',
                  border: theme === 'light' ? '1px solid #ddd' : '1px solid #555',
                  borderRadius: '8px'
                }}
              />
              <MiniMap 
                nodeColor={theme === 'light' ? '#667eea' : '#888'}
                maskColor={theme === 'light' ? 'rgba(0, 0, 0, 0.1)' : 'rgba(255, 255, 255, 0.1)'}
                style={{
                  background: theme === 'light' ? 'rgba(255, 255, 255, 0.9)' : 'rgba(45, 45, 45, 0.9)',
                  border: theme === 'light' ? '1px solid #ddd' : '1px solid #555',
                  borderRadius: '8px'
                }}
              />
            </ReactFlow>
          </div>
        </div>
      )}

      {isFullscreen && (
        <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
          <Button
            onClick={toggleFullscreen}
            style={{
              position: 'absolute',
              top: '16px',
              right: '16px',
              zIndex: 1000,
              background: theme === 'light'
                ? 'rgba(255, 255, 255, 0.95)'
                : 'rgba(45, 45, 45, 0.95)',
              backdropFilter: 'blur(10px)',
              border: 'none',
              borderRadius: '10px',
              padding: '10px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontWeight: 600,
              color: theme === 'light' ? '#2d3748' : '#e2e8f0',
              boxShadow: '0 4px 15px rgba(0, 0, 0, 0.2)'
            }}
          >
            <Minimize2 size={16} />
            Exit Fullscreen
          </Button>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            fitView
            minZoom={0.1}
            maxZoom={4}
          >
            <Background 
              variant={BackgroundVariant.Dots} 
              gap={16} 
              size={1}
              color={theme === 'light' ? '#ddd' : '#444'}
            />
            <Controls 
              style={{
                background: theme === 'light' ? 'rgba(255, 255, 255, 0.9)' : 'rgba(45, 45, 45, 0.9)',
                border: theme === 'light' ? '1px solid #ddd' : '1px solid #555',
                borderRadius: '8px'
              }}
            />
            <MiniMap 
              nodeColor={theme === 'light' ? '#667eea' : '#888'}
              maskColor={theme === 'light' ? 'rgba(0, 0, 0, 0.1)' : 'rgba(255, 255, 255, 0.1)'}
              style={{
                background: theme === 'light' ? 'rgba(255, 255, 255, 0.9)' : 'rgba(45, 45, 45, 0.9)',
                border: theme === 'light' ? '1px solid #ddd' : '1px solid #555',
                borderRadius: '8px'
              }}
            />
          </ReactFlow>
        </div>
      )}
    </div>
  );
}

const formatSources = (sources: sourcesResponse, currentDataset: number) => {
  const response: formattedSource[] = [];
  sources.datasets_by_connection.forEach((connection: DatasetsByConnection) => {
    connection.datasets.forEach((dataset: DatasetInfo) => {
      const csv_file = sources.csv_files.find(file => file.name === dataset.original_name);
      if (csv_file && dataset.dataset_id !== currentDataset) 
        response.push({
          connectionId: connection.connection_id,
          datasetId: dataset.dataset_id,
          originalName: dataset.original_name,
          size: csv_file.size,
          modifiedAt: csv_file.modified_at
        });
      }
    )
  });
  return response;
}
