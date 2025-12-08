/**
 * Sources
 */
export type uploadCSVResponse = {
    message: string,
    dataset_id: number,
    sha256: string,
    rows: number,
    filtered: boolean,
    eng_ids: number | null,
    saved_as: string
}

export type CsvFile = {
  name: string;
  size: number;
  modified_at: number;
};

export type DbConnection = {
  id: number;
  name: string;
  url: string;
  created_at: string;
  last_used_at: string | null;
  has_api_key: boolean;
};

export type DatasetInfo = {
  dataset_id: number;
  original_name: string;
  saved_path: string;
  sha256: string;
  rows_loaded: number;
  created_at: string;
};

export type DatasetsByConnection = {
  connection_id: number;
  connection_name: string;
  datasets: DatasetInfo[];
};

export type sourcesResponse = {
  csv_files: CsvFile[];
  db_connections: DbConnection[];
  datasets_by_connection: DatasetsByConnection[];
};

/**
 * Nodes
 */
export type rootNodeResponse = {
  root_nodes: string[];
  message: string;
  count: number;
  children_count: { [key: string]: number }
};

export type childNodeResponse = {
  search_id: string;
  parent: string;
  children: childNode[];
  count_children: number;
};

export type childNode = {
  id: string;
  name: string;
  sequence_no: number;
  level: number;
  num_children: number;
};

export type childPathResponse = {
  path: {
    path: nodeInPath[]
  },
  length: number
};

export type nodeInPath = {
  id: string,
  child_id: string,
  child_name: string
}