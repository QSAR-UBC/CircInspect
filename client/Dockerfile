FROM node:14-slim

WORKDIR /user/src/app 

COPY ./package.json ./

COPY ./yarn.lock ./

RUN npm install i

COPY . .

EXPOSE 3000

ENTRYPOINT [ "npm" ]

CMD ["start"]