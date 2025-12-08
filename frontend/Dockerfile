FROM node:24-alpine

WORKDIR /usr/src/frontend

COPY package*.json ./
RUN npm i

COPY . .
RUN npm run build

RUN chown -R node:node /usr/src/frontend
USER node

EXPOSE 5173
CMD ["npm", "run", "dev"]
