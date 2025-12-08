import type { AxiosRequestConfig } from "axios";
import { ApiService } from "./api-service";
import type { childNodeResponse, childPathResponse, rootNodeResponse } from "../responseTypes";

const apiPath = '/api'

export class NodeService extends ApiService{
    private xApiKey: string;
    private connectionId: number;
    private get config(): AxiosRequestConfig {
        return { headers: { 'x-api-key': this.xApiKey } };
    }

    constructor(baseUrl: string, xApiKey: string, connectionId: number) {
        super(`${baseUrl}${apiPath}`);
        this.xApiKey = xApiKey;
        this.connectionId = connectionId;
    }

    async getRootNode(datasetId: number): Promise<rootNodeResponse | null> {
        return await this.get(`/root_node?connection_id=${this.connectionId}&dataset_id=${datasetId}`, this.config);
    }

    async getChildNodes(datasetId: number, nodeId: string, numberChildren: number | null = null): Promise<childNodeResponse | null> {
        let limit = ""
        if (numberChildren) limit = `&limit=${numberChildren}`
        return await this.get(`/child_node?connection_id=${this.connectionId}&dataset_id=${datasetId}&node_id=${nodeId}${limit}`, this.config)
    }

    async getNodePath(datasetId: number, nodeId: string): Promise<childPathResponse | null> {
        return await this.get(`/sources/children/path/${nodeId}?connection_id=${this.connectionId}&dataset_id=${datasetId}`, this.config)
    }
}