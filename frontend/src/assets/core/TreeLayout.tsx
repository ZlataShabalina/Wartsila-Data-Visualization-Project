import type { Edge, Node } from '@xyflow/react';
import * as d3 from 'd3-hierarchy';
import type { nodeInPath } from '../responseTypes';

export class TreeLayout {
  root: d3.HierarchyNode<any>;
  treeLayout!: d3.TreeLayout<any>;
  nodeWidth: number;
  nodeHeight: number;
  spacing: number;
  nodes: any[];
  edges: any[];
  layout: 'horizontal' | 'vertical';

  constructor(data: any, nodeSize: [number, number], spacing: number, layout: 'vertical' | 'horizontal' = 'horizontal') {
    this.root = d3.hierarchy(data);
    [this.nodeWidth, this.nodeHeight] = nodeSize;
    this.spacing = spacing;
    this.layout = layout;
    this.nodes = [];
    this.edges = [];
    this.updateTreeLayout();
    console.log('');
    this.updateTree();
  }

  private updateTreeLayout() {

    if (this.layout === 'horizontal') {
      // For horizontal: vertical spacing between siblings, horizontal depth spacing
      this.treeLayout = d3.tree().nodeSize([this.nodeHeight + this.spacing, this.nodeWidth + this.spacing * 3]);
    } else {
      // For vertical: horizontal spacing between siblings, vertical depth spacing
      this.treeLayout = d3.tree().nodeSize([this.nodeWidth + this.spacing, this.nodeHeight + this.spacing * 3]);
    }
  }

  public setLayout(layout: 'horizontal' | 'vertical') {
    this.layout = layout;
    this.updateTreeLayout();
    this.updateTree();
  }

  public getLayout(): 'horizontal' | 'vertical' {
    return this.layout;
  }

  private updateTree() {
    this.treeLayout(this.root);
    this.nodes = [];
    this.edges = [];

    this.root.descendants().forEach(d => {
      const declaredNum = d.data.numChildren;
      const localChildrenCount = (d.data.children?.length ?? 0);
      let hasChildren = false;
      if (declaredNum) {
        hasChildren = declaredNum > localChildrenCount;
      }

      if (d.parent) {
        this.edges.push({
          id: `${d.parent.data.id}-${d.data.id}`,
          source: d.parent.data.id,
          target: d.data.id,
          type: 'smoothstep',
          animated: true
        });
      }

      const expanded = this.isExpanded(d.data.id);
      
      let position;
      if (this.layout === 'horizontal') {
        // Horizontal: root on left, expands to right
        // d3's x = vertical position, y = depth
        // We want: x = depth (left to right), y = vertical position
        position = { x: d.y, y: d.x };
      } else {
        // Vertical: root on top, expands downward
        // d3's x = horizontal position, y = depth
        // We want: x = horizontal position, y = depth (top to bottom)
        position = { x: d.x, y: d.y };
      }

      this.nodes.push({
        id: d.data.id,
        data: { 
          label: d.data.name, 
          numChildren: declaredNum, hasChildren, 
          expanded,
          layout: this.layout
        },
        position: position,
        style: { width: this.nodeWidth, height: this.nodeHeight },
        type: 'customNode'
      });
    });
  }

  public expandNode(nodeId: string, childData: any[]) {
    const target = this.root.descendants().find(d => d.data.id === nodeId);
    if (!target) return;
    if (!target.data.children) target.data.children = [];

    const existingIds = new Set((target.data.children ?? []).map((c: any) => c.id));
    const newChildren = childData.filter((child) => !existingIds.has(child.id));

    target.data.children.push(...newChildren);

    this.root = d3.hierarchy(this.root.data);
    this.updateTree();
  }

  public collapseNode(nodeId: string) {
    const target = this.root.descendants().find(d => d.data.id === nodeId);
    if (!target) return;
    target.data.children = [];
    this.root = d3.hierarchy(this.root.data);
    this.updateTree();
  }

  public getTreeLayout(): [Node[], Edge[]] {
    return [this.nodes, this.edges];
  }

  public isExpanded(nodeId: string): boolean {
    const target = this.root.descendants().find(d => d.data.id === nodeId);
    return (target?.data.children?.length ?? 0) > 0;
  }

  public numberOfChildren(nodeId: string): number {
    const target = this.root.descendants().find(d => d.data.id === nodeId);
    return target?.data.children?.length;
  }

    public expandPath(path: nodeInPath[]) {
    path.forEach((node: nodeInPath) => {
      if (node.child_id === "") return;
      const child = {
        id: node.child_id,
        name: node.child_name,
        children: [],
        hasChildren: false
      };
      this.expandNode(node.id, [child]);
    })
  }
}
