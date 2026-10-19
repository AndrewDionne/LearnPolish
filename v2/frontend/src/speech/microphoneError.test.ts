import {afterEach,describe,expect,test,vi} from 'vitest';
import {microphoneFailureMessage,readMicrophonePermission} from './microphoneError';

describe('Speak microphone errors are actionable without a second microphone request',()=>{
  afterEach(()=>vi.unstubAllGlobals());

  test('site already granted + denied capture points to macOS microphone privacy and input',()=>{
    const message=microphoneFailureMessage('NotAllowedError','granted');
    expect(message).toContain('already has microphone permission');
    expect(message).toContain('Privacy & Security');
    expect(message).toContain('Sound → Input');
    expect(message).not.toContain('Change Microphone to Allow');
  });

  test('site denied points to exact browser origin settings',()=>{
    const message=microphoneFailureMessage('NotAllowedError','denied');
    expect(message).toContain('exact site');
    expect(message).toContain('Microphone to Allow');
  });

  test('unknown permission covers browser AND macOS without asserting root cause',()=>{
    const message=microphoneFailureMessage('PermissionDeniedError','unknown');
    expect(message).toContain('browser');
    expect(message).toContain('macOS');
    expect(message).not.toContain('already has');
  });

  test('no device and capture errors do not falsely claim site permission denial',()=>{
    expect(microphoneFailureMessage('NotFoundError','granted')).toContain('No working microphone');
    expect(microphoneFailureMessage('NotReadableError','granted')).toContain('could not start');
    expect(microphoneFailureMessage('AbortError','unknown')).toContain('could not start');
    expect(microphoneFailureMessage('OverconstrainedError','granted')).toContain('recording settings');
    expect(microphoneFailureMessage('SecurityError','unknown')).toContain('security policy');
  });

  test('silent permission query reads only state, never getUserMedia',async()=>{
    const query=vi.fn().mockResolvedValue({state:'granted'});
    const mic=vi.fn();
    vi.stubGlobal('navigator',{permissions:{query},mediaDevices:{getUserMedia:mic}});
    expect(await readMicrophonePermission()).toBe('granted');
    expect(query).toHaveBeenCalledWith({name:'microphone'});
    expect(mic).not.toHaveBeenCalled();
  });

  test('unsupported and failing permissions queries safely return unknown',async()=>{
    vi.stubGlobal('navigator',{permissions:{query:vi.fn().mockRejectedValue(new Error('not supported'))}});
    expect(await readMicrophonePermission()).toBe('unknown');
    vi.stubGlobal('navigator',{mediaDevices:{getUserMedia:vi.fn()}});
    expect(await readMicrophonePermission()).toBe('unknown');
  });
});
