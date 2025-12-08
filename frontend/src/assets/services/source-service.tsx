import type { AxiosRequestConfig } from "axios";
import { ApiService } from "./api-service";
import type { sourcesResponse, uploadCSVResponse } from "../responseTypes";

const apiPath = '/api'

export class SourceService extends ApiService{
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

    async uploadCSV(formData: FormData): Promise<uploadCSVResponse | null> {
        return await this.post(`/upload_csv?connection_id=${this.connectionId}`, formData, this.config);
    }

    async getSources(): Promise<sourcesResponse | null> {
        return await this.get(`/sources?connection_id=${this.connectionId}`);
    }
}