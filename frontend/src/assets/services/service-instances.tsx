import { NodeService } from "./node-service";
import { SourceService } from "./source-service";

const baseUrl = import.meta.env.VITE_BASE_API_URL;
const connectionId = import.meta.env.VITE_CONNECTION_ID;
const xApiKey = import.meta.env.VITE_X_API_KEY;

export const nodeService = new NodeService(baseUrl, xApiKey, connectionId);
export const sourceService = new SourceService(baseUrl, xApiKey, connectionId);