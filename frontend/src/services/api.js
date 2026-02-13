import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_URL,
});

/**
 * Fetch available LLM models.
 * @returns {Promise<Array>} List of models
 */
export const getModels = async () => {
    const response = await api.get('/models');
    return response.data;
};

/**
 * Fetch chats with pagination.
 * @param {Object} params - { skip, limit }
 * @returns {Promise<Array>} List of chats
 */
export const getChats = async (params) => {
    const response = await api.get('/chats', { params });
    return response.data;
};

export const getChat = async (id) => {
    const response = await api.get(`/chats/${id}`);
    return response.data;
};

export const createChat = async (title) => {
    const response = await api.post('/chats', { title });
    return response.data;
};

export const deleteChat = async (id) => {
    const response = await api.delete(`/chats/${id}`);
    return response.data;
};

export const updateChat = async (id, data) => {
    const response = await api.patch(`/chats/${id}`, data);
    return response.data;
};

/**
 * Upload a file.
 * @param {File} file - File object
 * @param {boolean} overwrite - Whether to overwrite existing file
 * @returns {Promise<Object>} Uploaded attachment data
 */
export const uploadFile = async (file, overwrite = false) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('overwrite', overwrite);
    const response = await api.post('/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

// Streaming via EventSource is handled directly in components or a custom hook
export const getStreamUrl = () => `${API_URL}/chats/message`;

export default api;
