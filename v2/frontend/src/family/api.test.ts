import {describe,expect,test} from 'vitest';
import {familyServiceUrl} from './api';

describe('family API deployment and credential boundary',()=>{
 test('rejects insecure/wildcard/credentialled provider origins',()=>{
  expect(familyServiceUrl(undefined)).toBeNull();
  expect(familyServiceUrl('http://family.example.com')).toBeNull();
  expect(familyServiceUrl('https://family.example.com/api')).toBeNull();
  expect(familyServiceUrl('https://u:p@family.example.com/')).toBeNull();
  expect(familyServiceUrl('https://*.example.com/')).toBeNull();
  expect(familyServiceUrl('https://family.example.com')).toBe('https://family.example.com');
 });
 test('resolves explicitly selected same-origin Render hosting, never arbitrary hosts',()=>{
  expect(familyServiceUrl('same-origin','https://path-to-polish-v2.onrender.com'))
    .toBe('https://path-to-polish-v2.onrender.com');
  expect(familyServiceUrl('same-origin','http://insecure.example.org')).toBeNull();
  expect(familyServiceUrl('same-origin','http://127.0.0.1:4186'))
    .toBe('http://127.0.0.1:4186');
  expect(familyServiceUrl('same-origin')).toBeNull(); // no browser origin in Node tests
 });
 test('allows loopback development only under explicit configuration',()=>{
  expect(familyServiceUrl('http://localhost:8016/')).toBe('http://localhost:8016');
  expect(familyServiceUrl('http://127.0.0.1:8016/')).toBe('http://127.0.0.1:8016');
 });
});
