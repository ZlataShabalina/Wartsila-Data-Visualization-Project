import axios, { type AxiosRequestConfig } from "axios";

export class ApiService {
    private url: string;

    constructor(baseUrl: string) {
        this.url = baseUrl;
    }

    async get<T>(endpoint: string, config?: AxiosRequestConfig): Promise<T | null> {
        try {
            const resp = await axios.get<T>(`${this.url}${endpoint}`, config);
            return resp.data;
        } catch (err) {
            console.log('An error has occured', err)
            return null;
        };
    }

    async post<T>(endpoint:string, data?: any, config?: AxiosRequestConfig): Promise<T | null> {
        try {
            const resp = await axios.post<T>(`${this.url}${endpoint}`, data, config);
            return resp.data;
        } catch(err) {
            console.log('An error has occured', err)
            return null;
        }
    }
}