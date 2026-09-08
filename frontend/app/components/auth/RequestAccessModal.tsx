'use client';
import { Mail, X, KeyRound } from 'lucide-react';
import { Dialog } from '../workspace/Dialog';
interface Props { isOpen: boolean; onClose: () => void; isExpired?: boolean; productionName?: string; initialRole?: string }
export default function RequestAccessModal({ isOpen, onClose, isExpired }: Props) {
  const subject = encodeURIComponent(isExpired ? 'Lienmark — replacement invitation' : 'Lienmark — workspace access request');
  const body = encodeURIComponent('Hello,\n\nI would like access to a Lienmark production workspace.\n\nName:\nProduction:\nRequested responsibilities:\n\nThank you.');
  return <Dialog open={isOpen} onClose={onClose} label="Request workspace access">
    <div className="ws-dialog-header"><KeyRound size={25} /><button className="ws-icon-button" onClick={onClose} aria-label="Close access request"><X size={20} /></button></div>
    <h2>{isExpired ? 'Let’s restore your access.' : 'Your production. Your workspace.'}</h2>
    <p style={{ marginTop: 12 }}>A private invitation opens your assigned production and establishes your session. Your workspace administrator assigns your permissions.</p>
    <div className="ws-soft-box" style={{ marginTop: 20 }}><h3>Already invited?</h3><p>Open the private link you received. If it has expired or was already used, request a replacement. Never include an invitation token in your message.</p></div>
    <p style={{ marginTop: 16 }}>Draft a message to request access. Opening your email app does not submit a request automatically.</p>
    <div className="ws-dialog-actions"><button className="ws-button" onClick={onClose}>Keep exploring</button>
      <a className="ws-button primary" href={`mailto:singwane.linda.m@gmail.com?subject=${subject}&body=${body}`}><Mail size={15} />Draft access request</a></div>
  </Dialog>;
}