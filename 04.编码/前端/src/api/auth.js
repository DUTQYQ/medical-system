import request from '@/utils/request'
export const register = p => request.post('/auth/register', p)
export const login = p => request.post('/auth/login', p)
export const logout = () => request.post('/auth/logout')
export const getMe = () => request.get('/auth/me')
export const updateMe = p => request.put('/auth/me', p)
export const acceptPrivacy = () => request.post('/auth/privacy-consent', { accepted: true })
export const updatePassword = p => request.put('/auth/password', p)
