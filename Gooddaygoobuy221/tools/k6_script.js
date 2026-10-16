import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  vus: 10,
  duration: '10s',
};

export default function () {
  const url = `${__ENV.TARGET || 'https://example.com'}`;
  let res = http.get(url);
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(1);
}
