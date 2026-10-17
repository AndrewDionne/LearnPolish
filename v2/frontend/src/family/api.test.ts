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
 test('allows loopback development only under explicit configuration',()=>{
  expect(familyServiceUrl('http://localhost:8016/')).toBe('http://localhost:8016');
  expect(familyServiceUrl('http://127.0.0.1:8016/')).toBe('http://127.0.0.1:8016');
 });
});
