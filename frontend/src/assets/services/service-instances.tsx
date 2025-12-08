import { NodeService } from "./node-service";
import { SourceService } from "./source-service";

const baseUrl = 'http://localhost:8000'
const connectionId = 1;
const xApiKey = 'secret123'

export const nodeService = new NodeService(baseUrl, xApiKey, connectionId);
export const sourceService = new SourceService(baseUrl, xApiKey, connectionId);