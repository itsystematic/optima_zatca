import { useAppDispatch } from "@/app/hooks";
import { setCurrentPage } from "@/data/currentPage";
import { resetData } from "@/data/dataSlice";
import { WhatsAppOutlined } from "@ant-design/icons";
import { Button, Flex, Result } from "antd";

const Success = () => {
  const phoneNumber = "+201016649035";
  const dispatch = useAppDispatch();

  const handleHome = () => {
    // window.location.pathname = "/app";
    dispatch(resetData());
    dispatch(setCurrentPage(0));
  };
  const handleWhatsapp = () => {
    const url = `https://wa.me/${phoneNumber}`;
    window.open(url, "_blank");
  };
  return (
    <Flex align="center" justify="center" className="h-full">
      <Result
        status="success"
        title="Successfully Integerated With Zatca!"
        subTitle="Thank you for using our product. If you have any question you can contact us throgh Whatsapp!"
        extra={[
          <Button
            onClick={handleWhatsapp}
            className="bg-[#0cc143] text-white"
            key="whatsapp"
          >
            <Flex gap={10}>
              <div>
                <WhatsAppOutlined />
              </div>
              <div>WhatsApp</div>
            </Flex>
          </Button>,
          <Button onClick={handleHome} key="home">
            Back to board
          </Button>,
        ]}
      />
    </Flex>
  );
};

export default Success;
