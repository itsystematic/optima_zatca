import { useAppDispatch, useAppSelector } from "@/app/hooks";
import Loading from "@/components/Loading";
import { setIsAdding } from "@/data/addingState";
import { setCurrentPage } from "@/data/currentPage";
import { setStep } from "@/data/currentStep";
import { addCommercial, setData } from "@/data/dataSlice";
import { MainData } from "@/types";
import { Button, ConfigProvider, Table, TableProps, Tag } from "antd";
import React, { useEffect, useState } from "react";
import MainPage from "./MainPage";
import Welcome from "./Welcome";

const Home: React.FC = () => {
  const dispatch = useAppDispatch();
  const [mainData, setMainData] = useState<MainData[]>();
  const currentPage = useAppSelector((state) => state.pageReducer.currentPage);
  const currentData = useAppSelector(state => state.dataReducer);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    setLoading(true);
    if (isDev) {
      setMainData([]);
      setLoading(false);
      return;
    }
    frappe.call({
      method: "optima_zatca.zatca.api.get_companies_registered",
      callback: (r: { message: MainData[] }) => {
        if (r.message.length) {
          const company = r.message[0].company;
          const company_name_in_arabic = r.message[0].company_name_in_arabic;
          const tax_id = r.message[0].tax_id;
          const phase = r.message[0].phase;

          dispatch(setData({...currentData, company, company_name_in_arabic, tax_id, phase}))

          r.message.forEach((item) => {
            dispatch(
              addCommercial({
                commercial_register_name: item.commercial_register_name || "",
                commercial_register_number:
                  item.commercial_register_number || "",
                short_address: item.short_address || "",
                building_no: item.building_no || "",
                address_line1: item.address_line1 || "",
                address_line2: item.address_line2 || "",
                city: item.city || "",
                district: item.district || "",
                pincode: item.pincode || "",
                otp: item.otp || "",
                more_info: item.more_info || "",
                phase: item.phase,
              })
            );
          });
          setMainData(r.message);
        } else {
          setMainData([]);
        }
        setLoading(false);
      },
    });
  }, []);

  const columns: TableProps<MainData>["columns"] = [
    {
      title: "Commercial Register",
      children: [
        {
          title: __("Commercial Name"),
          dataIndex: "commercial_register_name",
          key: "commercial_register_name",
        },
        {
          title: __("Commercial Number"),
          dataIndex: "commercial_register_number",
          key: "commercial_register_number",
          width: "50px",
        },
      ],
    },
    {
      title: "Address",
      children: [
        {
          title: __("City"),
          dataIndex: "city",
          key: "city",
        },
        {
          title: __("Short Address"),
          dataIndex: "short_address",
          key: "short_address",
        },
        {
          title: __("Street"),
          dataIndex: "address_line1",
          key: "address_line1",
        },
        {
          title: __("Block"),
          children: [
            {
              title: __("Building No"),
              dataIndex: "building_no",
              key: "building_no",
              width: "20px",
            },
            {
              title: __("District"),
              dataIndex: "district",
              key: "district",
            },
          ],
        },
        {
          title: __("Secondary No"),
          dataIndex: "address_line2",
          key: "address_line2",
        },
      ],
    },
    {
      title: "Phase",
      dataIndex: "phase",
      key: "phase",
      render: (_, { phase }) => {
        let color;
        phase === "Phase 1" ? (color = "volcano") : (color = "geekblue");
        return (
          <>
            <Tag color={color} key={phase}>
              {phase}
            </Tag>
          </>
        );
      },
    },
    {
      title: __("Postal Code"),
      dataIndex: "pincode",
      key: "pincode",
      width: "20px",
    },
  ];

  return (
    <div className="h-screen w-full">
      {/* Show loading screen */}
      {loading ? (
        <Loading />
      ) : mainData?.length ? (
        currentPage ? (
          <MainPage />
        ) : (
          <div className="p-5 flex flex-col gap-2 h-full">
            <img
              src={
                isDev
                  ? "Tutorial.png"
                  : "/assets/optima_zatca/zatca-onboarding/Tutorial.png"
              }
              alt="Background"
              className="absolute top-0 left-0 h-full w-full bg-cover"
            />
            <ConfigProvider
              theme={{
                token: {
                  colorPrimary: "#483f61", // Custom primary color
                },
                components: {
                  Input: {
                    controlHeightLG: 48,
                    marginLG: 0,
                  },
                  Button: {
                    controlHeightLG: 48,
                  },
                  Modal: {
                    headerBg: "#f3f3f3",
                    contentBg: "#f3f3f3",
                  },
                  Table: {
                    headerBg: "#483f61",
                    headerColor: "#ffffff",
                  },
                },
              }}
            >
              <h1 className="text-4xl italic text-[#483f61] font-medium text-center z-10">
                {__("Current Commercial Registers")}
              </h1>
              <Button
                type="primary"
                onClick={() => {
                  dispatch(setCurrentPage(4));
                  dispatch(setIsAdding(true));
                  dispatch(setStep({ currentStep: 1 }));
                }}
                size="large"
                className="bg-[#483f61] disabled:opacity-90 disabled:text-white self-end w-1/6"
              >
                {__("ADD CR")}
              </Button>

              <Table
                dataSource={mainData}
                bordered
                columns={columns}
                className="h-full"
              />
            </ConfigProvider>
          </div>
        )
      ) : (
        // Page sliding view
        <Welcome />
      )}
    </div>
  );
};

export default Home;
