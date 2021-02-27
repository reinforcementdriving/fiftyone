import styled from "styled-components";

export const Box = styled.div`
  padding: 1em;
  box-sizing: border-box;
  border: 2px solid ${({ theme }) => theme.border};
  background-color: ${({ theme }) => theme.background};
`;

export const VerticalSpacer = styled.div`
  height: ${({ height }) =>
    typeof height == "number" ? height + "px" : height};
  background-color: ${({ opaque, theme }) =>
    opaque ? theme.background : undefined};
`;

export const Button = styled.button`
  display: flex;
  align-items: center;
  background-color: ${({ theme }) => theme.button};
  color: ${({ theme }) => theme.font};
  border: 1px solid ${({ theme }) => theme.buttonBorder};
  border-radius: 1px;
  margin: 0 3px;
  padding: 3px 10px;
  font-weight: bold;
  cursor: pointer;

  svg.MuiSvgIcon-root {
    font-size: 1.25em;
    margin-left: -3px;
    margin-right: 3px;
  }
`;

export const ModalWrapper = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: ${({ theme }) => theme.overlay};
`;

export const ModalFooter = styled.footer`
  display: flex;
  flex-shrink: 0;
  border-top: 2px solid ${({ theme }) => theme.border};
  padding: 1em;
  background-color: ${({ theme }) => theme.backgroundLight};
`;

export const scrollbarStyles = ({ theme }) => `
::-webkit-scrollbar {
  width: 16px;
}
scrollbar-width: none;
@-moz-document url-prefix() {
  padding-right: 16px;
}

::-webkit-scrollbar-track {
  border: solid 4px transparent ${theme.fontDarkest};
}

::-webkit-scrollbar-thumb {
  box-shadow: inset 0 0 10px 10px transparent;
  border: solid 4px transparent;
  border-radius: 16px;
  transition: box-shadow linear 0.5s;
}
&:hover::-webkit-scrollbar-thumb {
  box-shadow: inset 0 0 10px 10px ${theme.fontDarkest};
}
`;
